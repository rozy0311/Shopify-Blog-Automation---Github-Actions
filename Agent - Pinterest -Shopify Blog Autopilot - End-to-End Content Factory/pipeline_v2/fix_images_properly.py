#!/usr/bin/env python3
"""
Fix Images Properly - Restores Pinterest images + adds topic-specific AI images
Requirements:
1. Keep original Pinterest images as inline
2. Add 3 topic-specific AI inline images (Pollinations.ai + Shopify CDN)
3. Add 1 featured/main image (topic-specific)
4. NO duplicates
"""

import sys
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
import re
import json
import time
import os
import random
from urllib.parse import quote

# Shopify Config
SHOP = (os.environ.get("SHOPIFY_SHOP", "the-rike-inc.myshopify.com") or "").strip()
if "." not in SHOP or "myshopify.com" not in SHOP:
    print("⚠️ Invalid SHOPIFY_SHOP; falling back to the-rike-inc.myshopify.com")
    SHOP = "the-rike-inc.myshopify.com"
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "108441862462")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get("SHOPIFY_TOKEN")
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

if not TOKEN:
    raise SystemExit("Missing SHOPIFY_ACCESS_TOKEN")

# Pinterest matched data
MATCHED_DATA_FILE = "../scripts/matched_drafts_pinterest.json"

# Quality settings for Pollinations
QUALITY = "professional photography, high resolution, 8K, detailed, sharp focus, beautiful lighting"

# Optional vision review (auto-enable when key is present)
VISION_REVIEW = os.environ.get("VISION_REVIEW", "").lower() in {
    "1",
    "true",
    "yes",
}
VISION_API_BASE = os.environ.get(
    "VISION_API_BASE", "https://models.github.ai/inference"
)
VISION_MODEL_ID = os.environ.get("VISION_MODEL_ID", "openai/gpt-4o-mini")
VISION_API_KEY = os.environ.get("VISION_API_KEY", "")
if VISION_API_KEY and not VISION_REVIEW:
    VISION_REVIEW = True
VISION_TIMEOUT = int(os.environ.get("VISION_TIMEOUT", "30"))
VISION_MAX_ATTEMPTS = int(os.environ.get("VISION_MAX_ATTEMPTS", "6"))
VISION_RETRY_SLEEP = float(os.environ.get("VISION_RETRY_SLEEP", "6"))
VISION_BACKOFF_FACTOR = float(os.environ.get("VISION_BACKOFF_FACTOR", "1.8"))


def load_matched_data():
    """Load Pinterest matched data"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, MATCHED_DATA_FILE)

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"matched": []}


def get_pinterest_image_url(pin_id: str) -> str:
    """Get Pinterest image URL from pin ID"""
    # Pinterest CDN pattern
    return f"https://i.pinimg.com/736x/{pin_id[:2]}/{pin_id[2:4]}/{pin_id[4:6]}/{pin_id}.jpg"


def get_pollinations_url(
    prompt: str, width: int = 1200, height: int = 800, seed: int = 42
) -> str:
    """Get Pollinations.ai image URL"""
    encoded_prompt = quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={seed}&nologo=true"


def download_image(url: str, max_retries: int = 3) -> bytes:
    """Download image and return bytes"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"    📥 Downloading... (attempt {attempt})")
            response = requests.get(url, timeout=120)
            if response.status_code == 200 and len(response.content) > 10000:
                print(f"    ✅ Downloaded {len(response.content) // 1024}KB")
                return response.content
            else:
                print(f"    ⚠️ Response too small or failed, retrying...")
                time.sleep(5)
        except Exception as e:
            print(f"    ⚠️ Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(5)

    print(f"    ❌ Failed after {max_retries} attempts")
    return None


def _extract_json(text: str):
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


def vision_review_image(image_url: str):
    if not (VISION_REVIEW and VISION_API_KEY):
        return None

    payload = {
        "model": VISION_MODEL_ID,
        "temperature": 0,
        "max_tokens": 60,
        "messages": [
            {
                "role": "system",
                "content": "You are a strict image safety reviewer. Reply ONLY in JSON.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Check if the image contains any visible hands, fingers, or people. "
                            "Return JSON with keys: has_hands (true/false), has_people (true/false), "
                            "safe (true/false), reason (short)."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
    }

    try:
        resp = requests.post(
            f"{VISION_API_BASE.rstrip('/')}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {VISION_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=VISION_TIMEOUT,
        )
        if resp.status_code != 200:
            print(f"    ⚠️ Vision review failed: {resp.status_code}")
            return None

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return _extract_json(content)
    except Exception as e:
        print(f"    ⚠️ Vision review error: {e}")
        return None


def is_vision_safe(result) -> bool:
    if result is None:
        return False
    if result.get("has_hands") or result.get("has_people"):
        return False
    if result.get("safe") is False:
        return False
    return True


def generate_valid_pollinations_image(
    prompt: str,
    width: int,
    height: int,
    seed_base: int,
    max_attempts: int = VISION_MAX_ATTEMPTS,
    used_urls: set | None = None,
):
    used_urls = used_urls or set()
    for attempt in range(max_attempts):
        seed = seed_base + attempt
        poll_url = get_pollinations_url(prompt, width, height, seed=seed)
        if poll_url in used_urls:
            continue
        vision_result = vision_review_image(poll_url)
        if VISION_REVIEW and not is_vision_safe(vision_result):
            print(f"    ⚠️ Vision reject: {vision_result}")
            sleep_s = VISION_RETRY_SLEEP * (VISION_BACKOFF_FACTOR**attempt)
            time.sleep(min(sleep_s, 30))
            continue
        img_bytes = download_image(poll_url)
        if img_bytes:
            used_urls.add(poll_url)
            return img_bytes, poll_url, vision_result
        sleep_s = VISION_RETRY_SLEEP * (VISION_BACKOFF_FACTOR**attempt)
        time.sleep(min(sleep_s, 30))
    return None, None, None


def _extract_existing_image_urls(body_html: str) -> set:
    urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', body_html or "")
    return {url.strip() for url in urls if url}


def _seed_base(article_id: int) -> int:
    return int(time.time()) % 100000 + int(article_id) % 1000 + random.randint(1, 999)


def upload_to_shopify_cdn(image_bytes: bytes, filename: str) -> str:
    """Upload image to Shopify Files via GraphQL API"""
    headers = {
        "X-Shopify-Access-Token": TOKEN,
        "Content-Type": "application/json",
    }

    graphql_url = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"

    # Step 1: Get staged upload URL
    stage_query = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
      stagedUploadsCreate(input: $input) {
        stagedTargets {
          url
          resourceUrl
          parameters {
            name
            value
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    variables = {
        "input": [
            {
                "filename": filename,
                "mimeType": "image/jpeg",
                "resource": "FILE",
                "httpMethod": "POST",
                "fileSize": str(len(image_bytes)),
            }
        ]
    }

    response = requests.post(
        graphql_url,
        headers=headers,
        json={"query": stage_query, "variables": variables},
    )

    if response.status_code != 200:
        print(f"    ❌ Stage upload failed: {response.status_code}")
        return None

    data = response.json()
    staged = data.get("data", {}).get("stagedUploadsCreate", {})

    if staged.get("userErrors"):
        print(f"    ❌ User errors: {staged['userErrors']}")
        return None

    targets = staged.get("stagedTargets", [])
    if not targets:
        print("    ❌ No staged targets returned")
        return None

    target = targets[0]
    upload_url = target["url"]
    resource_url = target["resourceUrl"]
    params = {p["name"]: p["value"] for p in target["parameters"]}

    # Step 2: Upload to staged URL
    files = {
        **{k: (None, v) for k, v in params.items()},
        "file": (filename, image_bytes, "image/jpeg"),
    }

    upload_response = requests.post(upload_url, files=files)

    if upload_response.status_code not in [200, 201, 204]:
        print(f"    ❌ File upload failed: {upload_response.status_code}")
        return None

    # Step 3: Create file in Shopify
    create_query = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files {
          ... on MediaImage {
            id
            image {
              url
            }
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    create_variables = {
        "files": [
            {
                "originalSource": resource_url,
                "alt": filename.replace("_", " ").replace(".jpg", ""),
            }
        ]
    }

    create_response = requests.post(
        graphql_url,
        headers=headers,
        json={"query": create_query, "variables": create_variables},
    )

    if create_response.status_code != 200:
        return None

    create_data = create_response.json()
    files_result = create_data.get("data", {}).get("fileCreate", {})
    files_list = files_result.get("files", [])

    if files_list and files_list[0].get("image"):
        cdn_url = files_list[0]["image"]["url"]
        print(f"    ✅ CDN URL: {cdn_url[:60]}...")
        return cdn_url

    # Poll for CDN URL
    print("    ⏳ Waiting for CDN processing...")
    file_id = files_list[0].get("id") if files_list else None

    if file_id:
        for attempt in range(10):
            time.sleep(3)
            query = """
            query getFile($id: ID!) {
              node(id: $id) {
                ... on MediaImage {
                  image { url }
                }
              }
            }
            """
            resp = requests.post(
                graphql_url,
                headers=headers,
                json={"query": query, "variables": {"id": file_id}},
            )
            if resp.status_code == 200:
                node = resp.json().get("data", {}).get("node") or {}
                if node.get("image", {}).get("url"):
                    cdn_url = node["image"]["url"]
                    print(f"    ✅ CDN ready: {cdn_url[:60]}...")
                    return cdn_url

    return resource_url  # fallback


def generate_topic_specific_prompts(title: str) -> dict:
    """Generate image prompts that are SPECIFIC to the article topic"""

    title_lower = title.lower()

    # Extract main subject - more intelligent parsing
    main_subject = title
    for prefix in [
        "how to ",
        "the ",
        "a ",
        "an ",
        "complete guide to ",
        "guide to ",
        "diy ",
    ]:
        if title_lower.startswith(prefix):
            main_subject = title[len(prefix) :]
            break

    # Clean up
    main_subject = main_subject.split(":")[0].split("+")[0].split("|")[0].strip()
    if len(main_subject) > 50:
        main_subject = " ".join(main_subject.split()[:6])

    # Topic-specific keywords for better image matching
    topic_keywords = main_subject.lower()

    safety_suffix = "no people, no hands, no fingers, no faces"

    # Generate SPECIFIC prompts based on the topic
    prompts = {
        "featured": {
            "prompt": (
                f"Professional photograph of {main_subject}, natural lighting, high quality, "
                f"no text, no watermark, 16:9 aspect ratio, {QUALITY}, {safety_suffix}"
            ),
            "alt": f"{main_subject.title()} - Featured Image",
        },
        "inline1": {
            "prompt": (
                f"Materials and ingredients for {main_subject}, overhead flat lay, clean background, "
                f"professional photography, soft natural lighting, 4k, no text, no watermark, "
                f"{QUALITY}, {safety_suffix}"
            ),
            "alt": f"Materials for {main_subject}",
        },
        "inline2": {
            "prompt": (
                f"Step-by-step process showing {main_subject}, clean composition, professional photography, "
                f"soft natural lighting, 4k, no text, no watermark, {QUALITY}, {safety_suffix}"
            ),
            "alt": f"Process of {main_subject}",
        },
        "inline3": {
            "prompt": (
                f"Final result of {main_subject}, lifestyle setting, natural lighting, 4k, "
                f"no text, no watermark, {QUALITY}, {safety_suffix}"
            ),
            "alt": f"Completed {main_subject}",
        },
    }

    # Make prompts even MORE specific based on keywords
    if "vinegar" in topic_keywords or "ferment" in topic_keywords:
        prompts["inline1"][
            "prompt"
        ] = f"Fresh fruit scraps, apple peels, glass jars for making homemade vinegar, rustic kitchen setting, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Adding fruit scraps into glass jar with water for vinegar fermentation, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Beautiful homemade fruit vinegar in glass bottles, amber color, rustic labels, {QUALITY}"

    elif (
        "cordage" in topic_keywords
        or "rope" in topic_keywords
        or "fiber" in topic_keywords
    ):
        prompts["inline1"][
            "prompt"
        ] = f"Natural plant fibers for making cordage, bark strips, dried leaves, bushcraft materials, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Twisting natural plant fibers into strong rope using reverse wrap technique, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Finished natural cordage and handmade rope coiled beautifully, rustic outdoor setting, {QUALITY}"

    elif "cactus" in topic_keywords or "propagat" in topic_keywords:
        prompts["inline1"][
            "prompt"
        ] = f"Christmas cactus cuttings, small pots, potting soil, propagation supplies on table, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Carefully cutting christmas cactus segment for propagation, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Rooted christmas cactus cuttings in small pots, new growth, healthy plants, {QUALITY}"

    elif (
        "drip" in topic_keywords
        or "water" in topic_keywords
        or "bottle" in topic_keywords
    ):
        prompts["inline1"][
            "prompt"
        ] = f"Plastic soda bottles, scissors, drill, garden supplies for DIY drip irrigation, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Making holes in plastic bottle for drip feeder system, tools in action, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Completed bottle drip feeder watering plants in garden, sustainable irrigation, {QUALITY}"

    elif (
        "survival" in topic_keywords
        or "garden" in topic_keywords
        or "medicine" in topic_keywords
    ):
        prompts["inline1"][
            "prompt"
        ] = f"Seeds, medicinal herbs, garden tools for survival garden planning, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Planting medicinal herbs and vegetables in survival garden, soil and tools, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Thriving survival garden with medicinal plants and vegetables, abundant harvest, {QUALITY}"

    elif "pot" in topic_keywords or "planter" in topic_keywords:
        prompts["inline1"][
            "prompt"
        ] = f"Upcycled materials for DIY plant pots, cans, bottles, paint, crafting supplies, {QUALITY}"
        prompts["inline2"][
            "prompt"
        ] = f"Decorating and creating DIY plant pots from recycled materials, {QUALITY}"
        prompts["inline3"][
            "prompt"
        ] = f"Beautiful collection of handmade DIY plant pots with succulents and plants, {QUALITY}"

    elif "ginger" in topic_keywords or "nausea" in topic_keywords:
        prompts["inline1"][
            "prompt"
        ] = f"Fresh ginger root, lemon slices, honey, and a ceramic mug for ginger tea, clean kitchen counter, {QUALITY}, {safety_suffix}"
        prompts["inline2"][
            "prompt"
        ] = f"Ginger tea preparation setup with sliced ginger simmering in a small pot, steam rising, close-up, {QUALITY}, {safety_suffix}"
        prompts["inline3"][
            "prompt"
        ] = f"Finished ginger tea in a mug with sliced ginger beside it, calming setting, {QUALITY}, {safety_suffix}"

    elif (
        "cinder" in topic_keywords
        or "block" in topic_keywords
        or "outdoor" in topic_keywords
    ):
        prompts["inline1"][
            "prompt"
        ] = f"Cinder blocks, paint, brushes, and outdoor decor materials for DIY garden projects, {QUALITY}, {safety_suffix}"
        prompts["inline2"][
            "prompt"
        ] = f"Arranging and painting cinder blocks for outdoor garden decoration, {QUALITY}, {safety_suffix}"
        prompts["inline3"][
            "prompt"
        ] = f"Stunning cinder block garden furniture and planters in backyard, styled outdoor space, {QUALITY}, {safety_suffix}"

    for value in prompts.values():
        if safety_suffix not in value["prompt"].lower():
            value["prompt"] = f"{value['prompt']}, {safety_suffix}"

    return prompts


def count_existing_images(body_html: str) -> dict:
    """Count different types of images in article"""
    pinterest_imgs = len(re.findall(r'<img[^>]+src="[^"]*pinimg\.com[^"]*"', body_html))
    shopify_imgs = len(
        re.findall(r'<img[^>]+src="[^"]*cdn\.shopify\.com[^"]*"', body_html)
    )
    pollinations_imgs = len(
        re.findall(r'<img[^>]+src="[^"]*pollinations\.ai[^"]*"', body_html)
    )
    pexels_imgs = len(re.findall(r'<img[^>]+src="[^"]*pexels\.com[^"]*"', body_html))
    total = len(re.findall(r"<img[^>]+>", body_html))

    return {
        "pinterest": pinterest_imgs,
        "shopify_cdn": shopify_imgs,
        "pollinations": pollinations_imgs,
        "pexels": pexels_imgs,
        "total": total,
    }


def fix_article_images(
    article_id: int, pinterest_image_url: str = None, dry_run: bool = False
) -> bool:
    """
    Fix article images properly:
    1. Keep/restore Pinterest image
    2. Remove any off-topic or duplicate images
    3. Add topic-specific AI images
    """

    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

    # Get article
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Error fetching article {article_id}: {response.status_code}")
        return False

    article = response.json()["article"]
    title = article["title"]
    body_html = article["body_html"]
    existing_urls = _extract_existing_image_urls(body_html)

    print(f"\n{'='*60}")
    print(f"📝 {title}")
    print(f"   ID: {article_id}")

    # Count existing images
    img_counts = count_existing_images(body_html)
    print(
        f"   Current images: Pinterest={img_counts['pinterest']}, Shopify CDN={img_counts['shopify_cdn']}, Total={img_counts['total']}"
    )

    # Generate topic-specific prompts
    prompts = generate_topic_specific_prompts(title)
    print(f"\n🎨 Topic-specific prompts generated:")
    print(f"   Featured: {prompts['featured']['alt']}")
    print(f"   Inline1: {prompts['inline1']['alt']}")
    print(f"   Inline2: {prompts['inline2']['alt']}")
    print(f"   Inline3: {prompts['inline3']['alt']}")

    if not VISION_REVIEW:
        print("\n❌ VISION_REVIEW=1 is required to publish images.")
        return False
    if not VISION_API_KEY:
        print("\n❌ VISION_API_KEY is required for vision review.")
        return False

    if dry_run:
        print("\n🔍 DRY RUN - No changes made")
        return True

    # Step 1: Clean up body - remove ALL existing inline images
    # (We'll re-add Pinterest + new AI images properly)
    new_html = body_html

    # Remove all figure blocks with images
    new_html = re.sub(r"<figure[^>]*>[\s\S]*?</figure>", "", new_html)

    # Remove standalone img tags
    new_html = re.sub(r"<img[^>]+>", "", new_html)

    # Clean up empty paragraphs and extra whitespace
    new_html = re.sub(r"<p>\s*</p>", "", new_html)
    new_html = re.sub(r"\n{3,}", "\n\n", new_html)

    print(f"\n🧹 Cleaned existing images from body")

    # Step 2: Generate and upload new AI images
    print("\n🖼️ Generating topic-specific AI images...")

    cdn_urls = []
    used_poll_urls = set(existing_urls)
    used_cdn_urls = set(existing_urls)
    featured_b64 = None
    seed_base = _seed_base(article_id)

    # Featured image
    print("\n  [1/4] Featured image:")
    featured_bytes, _, _ = generate_valid_pollinations_image(
        prompts["featured"]["prompt"],
        1200,
        800,
        seed_base=seed_base,
        used_urls=used_poll_urls,
    )
    if featured_bytes:
        import base64

        featured_b64 = base64.b64encode(featured_bytes).decode("utf-8")

    # Inline images
    for i, key in enumerate(["inline1", "inline2", "inline3"], 1):
        print(f"\n  [{i+1}/4] {prompts[key]['alt']}:")
        img_bytes = None
        cdn_url = None
        for attempt in range(VISION_MAX_ATTEMPTS):
            img_bytes, _, _ = generate_valid_pollinations_image(
                prompts[key]["prompt"],
                1000,
                667,
                seed_base=seed_base + (i * 100) + attempt,
                used_urls=used_poll_urls,
            )
            if not img_bytes:
                continue
            cdn_url = upload_to_shopify_cdn(
                img_bytes, f"article_{article_id}_{key}_{attempt}.jpg"
            )
            if not cdn_url:
                continue
            if cdn_url in used_cdn_urls:
                print("    ⚠️ Duplicate CDN URL detected, regenerating...")
                sleep_s = VISION_RETRY_SLEEP * (VISION_BACKOFF_FACTOR**attempt)
                time.sleep(min(sleep_s, 30))
                continue
            used_cdn_urls.add(cdn_url)
            cdn_urls.append((cdn_url, prompts[key]["alt"]))
            break

    if featured_b64 is None or len(cdn_urls) < 3:
        print(
            f"\n❌ Image generation incomplete: featured={bool(featured_b64)} inline={len(cdn_urls)}/3"
        )
        print("   Skipping update to avoid bad images.")
        return False

    # Step 3: Add Pinterest image if available
    if pinterest_image_url:
        print(f"\n📌 Adding Pinterest image: {pinterest_image_url[:50]}...")

    # Step 4: Insert images into body
    paragraphs = list(re.finditer(r"</p>", new_html))
    total_paras = len(paragraphs)

    print(f"\n📝 Inserting images into {total_paras} paragraphs...")

    # Calculate positions for images
    images_to_insert = []

    # Pinterest image goes near the beginning (after 2nd paragraph)
    if pinterest_image_url and total_paras > 2:
        images_to_insert.append(
            {
                "pos_idx": 1,
                "url": pinterest_image_url,
                "alt": f"Pinterest: {title}",
                "source": "pinterest",
            }
        )

    # AI images distributed throughout
    def _even_positions(total: int, n: int) -> list[int]:
        if total <= 0:
            return []
        positions = []
        for idx in range(n):
            pos = int(((idx + 1) * total) / (n + 1))
            pos = max(0, min(total - 1, pos))
            positions.append(pos)
        # ensure unique and sorted
        return sorted(set(positions), reverse=False)

    ai_positions = _even_positions(total_paras, len(cdn_urls))
    if len(ai_positions) < len(cdn_urls):
        ai_positions = list(range(min(len(cdn_urls), total_paras)))

    for i, (cdn_url, alt) in enumerate(cdn_urls):
        if i < len(ai_positions):
            images_to_insert.append(
                {"pos_idx": ai_positions[i], "url": cdn_url, "alt": alt, "source": "ai"}
            )

    # Sort by position descending (insert from end to avoid position shifts)
    images_to_insert.sort(key=lambda x: x["pos_idx"], reverse=True)

    # Insert images
    for img in images_to_insert:
        pos_idx = img["pos_idx"]
        if pos_idx < len(paragraphs):
            pos = paragraphs[pos_idx].end()

            img_html = f"""
<figure style="margin: 30px auto; text-align: center; max-width: 900px;">
    <img src="{img['url']}" alt="{img['alt']}" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <figcaption style="font-style: italic; color: #666; margin-top: 10px; font-size: 0.9em;">{img['alt']}</figcaption>
</figure>
"""
            new_html = new_html[:pos] + img_html + new_html[pos:]
            # Re-find paragraphs after insertion
            paragraphs = list(re.finditer(r"</p>", new_html))

    # Step 5: Update article
    update_data = {
        "article": {"id": article_id, "body_html": new_html, "published": True}
    }

    # Add featured image if we have one
    if featured_b64:
        update_data["article"]["image"] = {
            "attachment": featured_b64,
            "alt": prompts["featured"]["alt"],
        }

    print("\n📤 Publishing updated article...")
    update_url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    update_resp = requests.put(update_url, headers=headers, json=update_data)

    if update_resp.status_code == 200:
        final_counts = count_existing_images(new_html)
        pinterest_count = 1 if pinterest_image_url else 0
        print(f"\n✅ SUCCESS!")
        print(f"   Pinterest images: {pinterest_count}")
        print(f"   AI inline images: {len(cdn_urls)}")
        print(f"   Featured image: {'Yes' if featured_b64 else 'No'}")
        return True
    else:
        print(f"\n❌ Failed to update: {update_resp.status_code}")
        print(update_resp.text[:200])
        return False


def fix_all_matched_articles(dry_run: bool = False):
    """Fix all matched Pinterest articles"""

    matched_data = load_matched_data()
    articles = matched_data.get("matched", [])

    print(f"\n{'='*60}")
    print(f"FIX IMAGES PROPERLY - {len(articles)} matched articles")
    print(f"{'='*60}")

    success = 0
    failed = 0

    for article in articles:
        article_id = article["draft_id"]
        pin_id = article.get("pin_id", "")

        # Try to get Pinterest image URL
        pinterest_url = None
        if pin_id:
            # Pinterest image URL pattern
            pinterest_url = f"https://i.pinimg.com/736x/{pin_id}.jpg"

        if fix_article_images(article_id, pinterest_url, dry_run):
            success += 1
        else:
            failed += 1

        # Rate limiting
        if not dry_run:
            time.sleep(2)

    print(f"\n{'='*60}")
    print(f"DONE: {success} success, {failed} failed")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix article images properly")
    parser.add_argument("--article-id", type=int, help="Single article ID to fix")
    parser.add_argument("--all", action="store_true", help="Fix all matched articles")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")
    args = parser.parse_args()

    if args.article_id:
        # Load matched data to get Pinterest URL
        matched_data = load_matched_data()
        pinterest_url = None
        for article in matched_data.get("matched", []):
            if article["draft_id"] == args.article_id:
                pin_id = article.get("pin_id", "")
                if pin_id:
                    pinterest_url = f"https://i.pinimg.com/736x/{pin_id}.jpg"
                break

        fix_article_images(args.article_id, pinterest_url, args.dry_run)
    elif args.all:
        fix_all_matched_articles(args.dry_run)
    else:
        print("Usage: python fix_images_properly.py --article-id ID [--dry-run]")
        print("       python fix_images_properly.py --all [--dry-run]")
