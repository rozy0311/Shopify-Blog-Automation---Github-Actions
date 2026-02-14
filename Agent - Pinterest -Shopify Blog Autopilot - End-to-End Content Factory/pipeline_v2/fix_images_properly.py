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
from pathlib import Path
from urllib.parse import quote

# Load .env from project
try:
    from dotenv import load_dotenv

    for p in [Path(__file__).parent.parent / ".env", Path(__file__).parent / ".env"]:
        if p.exists():
            load_dotenv(p)
            break
except ImportError:
    pass

# Shopify Config
SHOP = os.environ.get("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "108441862462")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get("SHOPIFY_TOKEN")
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

if not TOKEN:
    raise SystemExit("Missing SHOPIFY_ACCESS_TOKEN")

# Pinterest matched data
MATCHED_DATA_FILE = "../scripts/matched_drafts_pinterest.json"

# Quality settings for Pollinations - CINEMATIC REALISTIC STYLE
QUALITY = "hyper realistic, photorealistic, cinematic lighting, golden hour, shallow depth of field, bokeh, 8K resolution, shot on Sony A7R IV, 85mm f/1.4 lens, National Geographic quality"

# Realistic scene settings
SCENE_KITCHEN = "cozy farmhouse kitchen, wooden countertops, morning sunlight streaming through window, warm atmosphere, lived-in feel"
SCENE_GARDEN = "lush organic garden at golden hour, morning dew on leaves, rustic wooden raised beds, natural setting"
SCENE_TABLE = "rustic wooden farm table, vintage ceramic bowls, natural linen cloth, soft window light, hygge aesthetic"
SCENE_OUTDOOR = "beautiful outdoor setting, natural environment, soft diffused sunlight, authentic atmosphere"

# Optional vision review (disable by default)
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
VISION_TIMEOUT = 20
VISION_MAX_ATTEMPTS = 4


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
    """Get Pollinations.ai image URL.
    When POLLINATIONS_API_KEY is set: uses gen.pollinations.ai (paid tier) or GET_POLLINATIONS_URL.
    Otherwise: uses image.pollinations.ai (free tier).
    """
    encoded_prompt = quote(prompt)
    api_key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    base = (os.environ.get("GET_POLLINATIONS_URL", "") or "").strip().rstrip("/")

    if api_key and base:
        # Paid tier: use GET_POLLINATIONS_URL with /image/ path (enter/gen API)
        # gen.pollinations.ai requires model=flux parameter
        if "enter.pollinations.ai" in base:
            base = "https://gen.pollinations.ai"
        url = f"{base}/image/{encoded_prompt}?model=flux&width={width}&height={height}&seed={seed}&key={api_key}"
    elif api_key:
        # API key set but no custom base: use gen.pollinations.ai (paid tier)
        url = f"https://gen.pollinations.ai/image/{encoded_prompt}?model=flux&width={width}&height={height}&seed={seed}&key={api_key}"
    else:
        # Free tier: image.pollinations.ai
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={seed}&nologo=true"
    return url


def download_image(url: str, max_retries: int = 3) -> bytes:
    """Download image and return bytes"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"    📥 Downloading... (attempt {attempt})")
            response = requests.get(
                url,
                timeout=120,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            content_len = len(response.content)
            if response.status_code == 200 and content_len > 10000:
                print(f"    ✅ Downloaded {len(response.content) // 1024}KB")
                return response.content
            else:
                preview = response.content[:120].decode("utf-8", errors="replace")
                print(
                    f"    ⚠️ Response status {response.status_code}, size {content_len} bytes"
                )
                if preview.strip():
                    print(f"    ⚠️ Response preview: {preview}")
                print("    ⚠️ Response too small or failed, retrying...")
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
    if not result:
        return True
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
):
    for attempt in range(max_attempts):
        seed = seed_base + attempt
        poll_url = get_pollinations_url(prompt, width, height, seed=seed)
        vision_result = vision_review_image(poll_url)
        if vision_result and not is_vision_safe(vision_result):
            print(f"    ⚠️ Vision reject: {vision_result}")
            continue
        img_bytes = download_image(poll_url)
        if img_bytes:
            return img_bytes, poll_url, vision_result
    return None, None, None


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

    # Extract REAL topic from title - smarter parsing
    # If title has ":" take the part with actual topic keywords
    main_subject = title

    if ":" in title:
        parts = title.split(":")
        # Check which part has more topic-relevant words
        topic_words = [
            "grow",
            "plant",
            "herb",
            "garden",
            "diy",
            "make",
            "recipe",
            "homemade",
            "natural",
            "organic",
            "seed",
            "soil",
            "compost",
            "remedy",
            "health",
            "tea",
            "vinegar",
            "ferment",
            "preserve",
            "vapor",
            "rub",
            "salve",
            "balm",
            "tincture",
            "syrup",
        ]

        # List of specific nouns (plants, ingredients, things)
        specific_nouns = [
            "basil",
            "lavender",
            "mint",
            "tomato",
            "pepper",
            "bay leaf",
            "bay leaves",
            "cinnamon",
            "ginger",
            "garlic",
            "honey",
            "lemon",
            "apple",
            "fruit",
            "vegetable",
            "flower",
            "tree",
            "greenhouse",
            "walipini",
            "kombucha",
            "kefir",
            "sourdough",
            "vinegar",
            "jam",
            "vapor rub",
            "chest rub",
            "salve",
            "balm",
            "candle",
            "soap",
            "elderberry",
            "chamomile",
            "calendula",
            "aloe",
            "moringa",
            "neem",
        ]

        scores = []
        for part in parts:
            part_lower = part.lower()
            score = sum(1 for w in topic_words if w in part_lower)
            # Also check for specific nouns (plants, ingredients)
            if any(x in part_lower for x in specific_nouns):
                score += 3
            scores.append((score, part.strip()))

        # Pick the part with highest topic relevance
        scores.sort(reverse=True)
        main_subject = scores[0][1] if scores[0][0] > 0 else parts[-1].strip()

    # Remove common prefixes (loop through ALL matching prefixes)
    prefixes_to_remove = [
        "how to ",
        "the ",
        "a ",
        "an ",
        "complete guide to ",
        "guide to ",
        "diy ",
        "unlocking ",
        "unlock ",
        "harnessing ",
        "harness ",
        "power of ",
        "the power of ",
        "benefits of ",
        "uses of ",
        "safe ",
        "easy ",
        "simple ",
        "beginner ",
        "growing ",
        "making ",
    ]

    # Apply multiple prefix removals
    changed = True
    while changed:
        changed = False
        for prefix in prefixes_to_remove:
            if main_subject.lower().startswith(prefix):
                main_subject = main_subject[len(prefix) :]
                changed = True
                break

    # Clean up trailing words
    suffixes_to_remove = [
        " guide",
        " tutorial",
        " tips",
        " ideas",
        " recipe",
        " comfort",
        " relief",
        " remedies",
        " benefits",
    ]
    for suffix in suffixes_to_remove:
        if main_subject.lower().endswith(suffix):
            main_subject = main_subject[: -len(suffix)]
            break

    # Clean up
    main_subject = main_subject.split("+")[0].split("|")[0].strip()
    if len(main_subject) > 50:
        main_subject = " ".join(main_subject.split()[:6])

    # Final cleanup - remove "in Containers" type suffixes for cleaner prompts
    container_patterns = [
        " in containers",
        " in pots",
        " at home",
        " indoors",
        " outdoors",
    ]
    for pattern in container_patterns:
        if main_subject.lower().endswith(pattern):
            # Keep it but simplify for image prompt
            break

    # Ensure we have a meaningful subject
    if len(main_subject) < 3:
        main_subject = title.split(":")[0].strip() if ":" in title else title

    # Topic-specific keywords for better image matching
    topic_keywords = main_subject.lower()

    # Positive constraints to reduce hands/people without explicit bans
    safety_suffix = "no people visible, no hands, no fingers, still life composition"

    # AUTO-SELECT best scene based on topic keywords
    outdoor_keywords = [
        "garden",
        "plant",
        "grow",
        "soil",
        "seed",
        "compost",
        "outdoor",
        "yard",
        "lawn",
        "tree",
        "flower",
        "vegetable",
        "fruit",
        "harvest",
    ]
    kitchen_keywords = [
        "cook",
        "recipe",
        "tea",
        "soup",
        "food",
        "honey",
        "vinegar",
        "ferment",
        "preserve",
        "jam",
        "syrup",
        "bake",
        "bread",
    ]
    craft_keywords = [
        "diy",
        "make",
        "craft",
        "build",
        "sew",
        "knit",
        "paint",
        "upcycle",
        "recycle",
        "homemade",
    ]
    wellness_keywords = [
        "remedy",
        "herb",
        "medicine",
        "health",
        "natural",
        "essential",
        "oil",
        "balm",
        "salve",
        "tincture",
    ]

    # Determine best scene for this topic
    if any(kw in topic_keywords for kw in outdoor_keywords):
        primary_scene = SCENE_GARDEN
        secondary_scene = SCENE_OUTDOOR
        scene_type = "garden"
    elif any(kw in topic_keywords for kw in kitchen_keywords):
        primary_scene = SCENE_KITCHEN
        secondary_scene = SCENE_TABLE
        scene_type = "kitchen"
    elif any(kw in topic_keywords for kw in craft_keywords):
        primary_scene = "bright creative workshop with natural light, craft supplies organized neatly, maker space aesthetic"
        secondary_scene = SCENE_TABLE
        scene_type = "craft"
    elif any(kw in topic_keywords for kw in wellness_keywords):
        primary_scene = "serene apothecary setting, dried herbs hanging, amber glass bottles, natural wellness sanctuary"
        secondary_scene = SCENE_TABLE
        scene_type = "wellness"
    else:
        # Smart default based on common sustainable living topics
        primary_scene = SCENE_TABLE
        secondary_scene = SCENE_OUTDOOR
        scene_type = "lifestyle"

    # Generate CINEMATIC REALISTIC prompts with AUTO-SELECTED scenes
    prompts = {
        "featured": {
            "prompt": (
                f"Stunning hero shot of {main_subject} in {primary_scene}, beautifully styled like a magazine cover, "
                f"dramatic golden hour lighting from behind, shallow depth of field with creamy bokeh, "
                f"{QUALITY}, {safety_suffix}, no text, no logos, no watermark"
            ),
            "alt": "Hero image for this sustainable living project",
        },
        "inline1": {
            "prompt": (
                f"Overhead cinematic shot showing all elements for {main_subject} artfully arranged on {SCENE_TABLE}, "
                f"organic textures, morning light creating soft shadows, natural props like wooden boards and fresh greenery, "
                f"{QUALITY}, {safety_suffix}, no text, no logos, no watermark"
            ),
            "alt": "Essential materials and ingredients laid out",
        },
        "inline2": {
            "prompt": (
                f"Close-up macro photography capturing the essence of {main_subject}, dramatic depth of field, "
                f"beautiful details visible, natural moisture or texture, moody atmospheric lighting, "
                f"raw authentic moment captured, {QUALITY}, {safety_suffix}, no text, no logos, no watermark"
            ),
            "alt": "Close-up detail showing craftsmanship and texture",
        },
        "inline3": {
            "prompt": (
                f"Breathtaking final result of {main_subject} in {secondary_scene}, "
                f"styled like a Pinterest-worthy lifestyle photo, warm inviting atmosphere, "
                f"aspirational aesthetic that inspires action, {QUALITY}, {safety_suffix}, no text, no logos, no watermark"
            ),
            "alt": "Beautiful finished result ready to enjoy",
        },
    }

    # Make prompts CINEMATIC and REALISTIC based on keywords
    if "vinegar" in topic_keywords or "ferment" in topic_keywords:
        prompts["featured"]["prompt"] = (
            f"Hero shot of homemade fruit vinegar bottles on rustic farmhouse shelf, golden amber liquid glowing in sunlight, "
            f"vintage glass bottles with handwritten labels, morning rays through dusty window, {QUALITY}, {safety_suffix}"
        )
        prompts["inline1"]["prompt"] = (
            f"Overhead cinematic shot of fresh apple peels and fruit scraps with glass mason jars on aged wooden table, "
            f"natural kitchen light, scattered fresh herbs, artisanal preparation scene, {QUALITY}, {safety_suffix}"
        )
        prompts["inline2"]["prompt"] = (
            f"Close-up macro of fruit scraps fermenting in glass jar, beautiful bubbles rising, amber liquid, "
            f"dramatic side lighting creating depth, scientific yet beautiful, {QUALITY}, {safety_suffix}"
        )
        prompts["inline3"]["prompt"] = (
            f"Stunning presentation of finished homemade vinegar collection in vintage bottles, "
            f"rustic wooden pantry shelf, soft warm lighting, cozy homestead aesthetic, {QUALITY}, {safety_suffix}"
        )

    elif (
        "cordage" in topic_keywords
        or "rope" in topic_keywords
        or "fiber" in topic_keywords
    ):
        prompts["featured"]["prompt"] = (
            f"Cinematic shot of natural handmade cordage coiled on weathered driftwood, forest background with soft focus, "
            f"golden hour light filtering through trees, bushcraft wilderness aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline1"]["prompt"] = (
            f"Close-up of natural plant fibers, bark strips and dried leaves arranged on moss-covered log, "
            f"morning dew droplets visible, enchanted forest atmosphere, {QUALITY}, {safety_suffix}"
        )
        prompts["inline2"]["prompt"] = (
            f"Artistic shot of natural fibers mid-twist into rope strands, soft bokeh background of forest, "
            f"sunlight catching individual fiber strands, craftsman aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline3"]["prompt"] = (
            f"Beautiful finished natural cordage rope coiled elegantly next to campfire, wilderness survival scene, "
            f"warm firelight glow, rustic outdoor adventure aesthetic, {QUALITY}, {safety_suffix}"
        )

    elif "cactus" in topic_keywords or "propagat" in topic_keywords:
        prompts["featured"]["prompt"] = (
            f"Stunning hero shot of blooming Christmas cactus in terracotta pot, soft pink flowers in focus, "
            f"bright window light, modern boho home interior, lifestyle magazine quality, {QUALITY}, {safety_suffix}"
        )
        prompts["inline1"]["prompt"] = (
            f"Overhead shot of cactus cuttings with tiny terracotta pots and fresh soil on marble surface, "
            f"morning light creating soft shadows, minimalist plant parent aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline2"]["prompt"] = (
            f"Macro close-up of Christmas cactus segment showing root nodes, moisture droplets visible, "
            f"dramatic shallow depth of field, botanical photography style, {QUALITY}, {safety_suffix}"
        )
        prompts["inline3"]["prompt"] = (
            f"Row of successfully propagated cactus babies in small pots on sunny windowsill, "
            f"new growth visible, cozy plant corner aesthetic, aspirational home decor, {QUALITY}, {safety_suffix}"
        )

    elif (
        "drip" in topic_keywords
        or "irrigation" in topic_keywords
        or "water" in topic_keywords
    ):
        prompts["featured"]["prompt"] = (
            f"Beautiful DIY drip irrigation system in lush vegetable garden, water droplets catching sunlight, "
            f"healthy green plants, sustainable gardening scene, golden hour, {QUALITY}, {safety_suffix}"
        )
        prompts["inline1"]["prompt"] = (
            f"Overhead flat lay of upcycled bottles and garden tools for DIY irrigation on weathered potting bench, "
            f"garden gloves, seeds packets, vintage gardening aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline2"]["prompt"] = (
            f"Close-up of water droplet falling from homemade bottle dripper onto plant root, "
            f"slow motion frozen moment, crystal clear water, satisfying detail, {QUALITY}, {safety_suffix}"
        )
        prompts["inline3"]["prompt"] = (
            f"Thriving vegetable garden row with bottle drip feeders working, tomatoes ripening, "
            f"morning dew, abundant harvest scene, sustainable living aesthetic, {QUALITY}, {safety_suffix}"
        )

    elif (
        "survival" in topic_keywords
        or "medicinal" in topic_keywords
        or "herb" in topic_keywords
    ):
        prompts["featured"]["prompt"] = (
            f"Breathtaking survival medicine garden at golden hour, rows of medicinal herbs in full bloom, "
            f"rustic wooden markers, mountain backdrop, homesteading dream scene, {QUALITY}, {safety_suffix}"
        )
        prompts["inline1"]["prompt"] = (
            f"Overhead shot of heirloom seed packets and medicinal herb bundles on aged wooden table, "
            f"vintage garden journal, dried lavender, apothecary aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline2"]["prompt"] = (
            f"Close-up of hands-free shot of fresh medicinal herbs like chamomile and calendula in woven basket, "
            f"dew drops on petals, morning garden harvest aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline3"]["prompt"] = (
            f"Abundant medicinal herb garden in full glory, butterflies and bees, rustic fence background, "
            f"cottage garden dream, peaceful homestead vibes, {QUALITY}, {safety_suffix}"
        )

    elif "pot" in topic_keywords or "planter" in topic_keywords:
        prompts["featured"]["prompt"] = (
            f"Gorgeous collection of DIY upcycled planters on sunny balcony, succulents and trailing plants, "
            f"urban jungle aesthetic, creative recycled containers, lifestyle photo quality, {QUALITY}, {safety_suffix}"
        )
        prompts["inline1"]["prompt"] = (
            f"Overhead craft setup with paint cans, brushes, and recycled containers ready for transformation, "
            f"colorful artistic scene, creative workshop aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline2"]["prompt"] = (
            f"Close-up of beautifully painted upcycled tin can planter with trailing succulent, "
            f"artistic brush strokes visible, handmade craft aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline3"]["prompt"] = (
            f"Stunning vertical garden of DIY planters on rustic wooden pallet, various plants thriving, "
            f"small space gardening inspiration, Pinterest-worthy scene, {QUALITY}, {safety_suffix}"
        )

    elif (
        "ginger" in topic_keywords
        or "nausea" in topic_keywords
        or "tea" in topic_keywords
    ):
        prompts["featured"]["prompt"] = (
            f"Steaming cup of fresh ginger tea on cozy wooden table, cinnamon sticks and honey jar nearby, "
            f"soft morning light, warm comfort scene, hygge aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline1"]["prompt"] = (
            f"Overhead shot of fresh ginger root, lemon wedges, and local honey on marble cutting board, "
            f"natural remedy ingredients, wellness aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline2"]["prompt"] = (
            f"Close-up of ginger slices simmering in small copper pot, steam rising dramatically, "
            f"bubbles visible, aromatic kitchen moment, {QUALITY}, {safety_suffix}"
        )
        prompts["inline3"]["prompt"] = (
            f"Cozy scene of finished ginger tea in ceramic mug with knitted cozy, reading nook setting, "
            f"rainy window background, ultimate comfort aesthetic, {QUALITY}, {safety_suffix}"
        )

    elif (
        "cinder" in topic_keywords
        or "block" in topic_keywords
        or "outdoor" in topic_keywords
    ):
        prompts["featured"]["prompt"] = (
            f"Stunning cinder block garden furniture set in dreamy backyard, string lights overhead, "
            f"cushions and plants, outdoor living room aesthetic, sunset golden hour, {QUALITY}, {safety_suffix}"
        )
        prompts["inline1"]["prompt"] = (
            f"Flat lay of cinder blocks, outdoor paint colors, and gardening tools on concrete patio, "
            f"DIY project preparation, creative outdoor workspace, {QUALITY}, {safety_suffix}"
        )
        prompts["inline2"]["prompt"] = (
            f"Close-up of painted cinder block planter with cascading flowers, texture detail visible, "
            f"upcycled garden decor aesthetic, {QUALITY}, {safety_suffix}"
        )
        prompts["inline3"]["prompt"] = (
            f"Complete cinder block garden transformation with bench, planters and raised beds, "
            f"lush plants, string lights, magical outdoor oasis, {QUALITY}, {safety_suffix}"
        )

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


def extract_pinterest_urls(body_html: str) -> list[str]:
    return re.findall(r'<img[^>]+src="([^"]*pinimg\.com[^"]*)"', body_html)


def fix_article_images(
    article_id: int,
    pinterest_image_url: str = None,
    dry_run: bool = False,
    images_only: bool = False,
) -> bool:
    """
    Fix article images properly:
    1. Keep/restore Pinterest image
    2. Remove any off-topic or duplicate images (unless images_only=True)
    3. Add topic-specific AI images

    images_only: If True, only ADD missing images; do NOT remove/modify existing content.
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
    # Consider featured only if image has a valid src (Shopify CDN or other URL)
    img_obj = article.get("image") or {}
    featured_src = (img_obj.get("src") or "").strip()
    has_featured = bool(
        featured_src
        and ("cdn.shopify.com" in featured_src or featured_src.startswith("http"))
    )

    print(f"\n{'='*60}")
    print(f"📝 {title}")
    print(f"   ID: {article_id}")
    if images_only:
        print(f"   Mode: IMAGES ONLY (add missing, preserve content)")

    # Count existing images
    img_counts = count_existing_images(body_html)
    print(
        f"   Current images: Pinterest={img_counts['pinterest']}, Shopify CDN={img_counts['shopify_cdn']}, Total={img_counts['total']}"
    )
    print(
        f"   Featured image: {'Yes' if has_featured else 'No'}"
        + (f" ({featured_src[:50]}...)" if featured_src else "")
    )

    # Preserve an existing Pinterest image if none matched
    if not pinterest_image_url:
        existing_pins = extract_pinterest_urls(body_html)
        if existing_pins:
            pinterest_image_url = existing_pins[0]

    # images_only: skip if already has enough
    if images_only:
        need_inline = max(0, 3 - img_counts["total"])
        need_featured = not has_featured
        if need_inline == 0 and not need_featured:
            print("\n✅ Already has 3+ inline + featured; nothing to add.")
            return True
        print(
            f"   Need: +{need_inline} inline, featured={'Yes' if need_featured else 'No'}"
        )

    # Generate topic-specific prompts
    prompts = generate_topic_specific_prompts(title)
    print(f"\n🎨 Topic-specific prompts generated:")
    print(f"   Featured: {prompts['featured']['alt']}")
    print(f"   Inline1: {prompts['inline1']['alt']}")
    print(f"   Inline2: {prompts['inline2']['alt']}")
    print(f"   Inline3: {prompts['inline3']['alt']}")

    if dry_run:
        print("\n🔍 DRY RUN - No changes made")
        return True

    # Step 1: Clean body (unless images_only - preserve all content)
    new_html = body_html
    if not images_only:
        # Remove all figure blocks with images
        new_html = re.sub(r"<figure[^>]*>[\s\S]*?</figure>", "", new_html)
        # Remove standalone img tags
        new_html = re.sub(r"<img[^>]+>", "", new_html)
        # Clean up empty paragraphs and extra whitespace
        new_html = re.sub(r"<p>\s*</p>", "", new_html)
        new_html = re.sub(r"\n{3,}", "\n\n", new_html)
        print(f"\n🧹 Cleaned existing images from body")
    else:
        print(f"\n🧹 Keeping all content; only adding missing images")

    # Step 2: Generate and upload new AI images
    need_inline = (3 - img_counts["total"]) if images_only else 3
    need_featured = (not has_featured) if images_only else True
    need_inline = max(0, need_inline)

    print("\n🖼️ Generating topic-specific AI images...")

    cdn_urls = []
    featured_cdn_url = None

    # Featured image (only if needed) - upload to CDN then use src (more reliable than base64)
    if need_featured:
        print("\n  [1/4] Featured image:")
        featured_bytes, _, _ = generate_valid_pollinations_image(
            prompts["featured"]["prompt"],
            1200,
            800,
            seed_base=article_id % 1000,
        )
        if featured_bytes:
            featured_cdn_url = upload_to_shopify_cdn(
                featured_bytes, f"article_{article_id}_featured.jpg"
            )
    else:
        print("\n  [1/4] Featured image: already present, skip")

    # Inline images (only as many as needed; when images_only and need_inline=0, skip)
    keys_needed = ["inline1", "inline2", "inline3"][:need_inline] if need_inline else []
    for i, key in enumerate(keys_needed, 1):
        print(f"\n  [{i+1}/4] {prompts[key]['alt']}:")
        img_bytes, _, _ = generate_valid_pollinations_image(
            prompts[key]["prompt"],
            1000,
            667,
            seed_base=article_id % 1000 + i,
        )
        if img_bytes:
            cdn_url = upload_to_shopify_cdn(
                img_bytes, f"article_{article_id}_{key}.jpg"
            )
            if cdn_url:
                cdn_urls.append((cdn_url, prompts[key]["alt"]))

    # Step 3: Guardrail (relaxed when images_only - partial add is OK)
    if images_only:
        if len(cdn_urls) == 0 and not featured_cdn_url:
            print("\n❌ No new images generated; nothing to add.")
            return False
    else:
        required_inline = 3
        required_featured = True
        if len(cdn_urls) < required_inline or (
            required_featured and not featured_cdn_url
        ):
            print("\n❌ Image generation incomplete; skipping publish.")
            print(f"   AI inline images: {len(cdn_urls)}/{required_inline}")
            print(f"   Featured image: {'Yes' if featured_cdn_url else 'No'}")
            return False

    # Step 4: Upload Pinterest image to Shopify CDN (hotlink protection bypass)
    pinterest_cdn_url = None
    if not images_only and pinterest_image_url:
        print(f"\n📌 Uploading Pinterest image to CDN: {pinterest_image_url[:50]}...")
        try:
            # Download Pinterest image
            pin_resp = requests.get(
                pinterest_image_url,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            if pin_resp.status_code == 200 and len(pin_resp.content) > 1000:
                # Upload to Shopify CDN
                pin_filename = f"pinterest_{article_id}_{int(time.time())}.jpg"
                pinterest_cdn_url = upload_to_shopify_cdn(
                    pin_resp.content, pin_filename
                )
                if pinterest_cdn_url:
                    print(
                        f"    ✅ Pinterest uploaded to CDN: {pinterest_cdn_url[:60]}..."
                    )
                else:
                    print(f"    ⚠️ Pinterest CDN upload failed, skipping")
            else:
                print(f"    ⚠️ Pinterest download failed: {pin_resp.status_code}")
        except Exception as e:
            print(f"    ⚠️ Pinterest upload error: {e}")

    # Step 5: Insert images into body
    paragraphs = list(re.finditer(r"</p>", new_html))
    total_paras = len(paragraphs)

    print(f"\n📝 Inserting images into {total_paras} paragraphs...")

    # Calculate positions for images
    images_to_insert = []

    # Pinterest image (only when full fix - not images_only) - use CDN URL
    if not images_only and pinterest_cdn_url and total_paras > 2:
        images_to_insert.append(
            {
                "pos_idx": 1,
                "url": pinterest_cdn_url,
                "alt": "Pinterest inspiration for this project",
                "source": "pinterest",
            }
        )

    # AI images distributed throughout
    if total_paras >= 9:
        ai_positions = [3, total_paras // 2, total_paras - 3]
    elif total_paras >= 6:
        ai_positions = [2, 4, total_paras - 2]
    else:
        ai_positions = (
            [1, 2, 3] if total_paras >= 4 else list(range(min(3, total_paras)))
        )

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

    # Step 6: Update article
    update_data = {
        "article": {"id": article_id, "body_html": new_html, "published": True}
    }

    # Add featured image if we have one (use src=CDN URL - more reliable than base64)
    if featured_cdn_url:
        update_data["article"]["image"] = {
            "src": featured_cdn_url,
            "alt": prompts["featured"]["alt"],
        }
        print(f"\n🖼️ Setting featured image: {prompts['featured']['alt']}")

    print("\n📤 Publishing updated article...")
    update_url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    update_resp = requests.put(update_url, headers=headers, json=update_data)

    if update_resp.status_code == 200:
        pinterest_count = 1 if pinterest_cdn_url else 0
        print(f"\n✅ SUCCESS!")
        print(f"   Pinterest images (CDN): {pinterest_count}")
        print(f"   AI inline images: {len(cdn_urls)}")
        print(f"   Featured image: {'Yes' if featured_cdn_url else 'No'}")
        return True
    else:
        print(f"\n❌ Failed to update: {update_resp.status_code}")
        print(update_resp.text[:200])
        return False


def fix_all_matched_articles(dry_run: bool = False, images_only: bool = False):
    """Fix all matched Pinterest articles"""

    matched_data = load_matched_data()
    articles = matched_data.get("matched", [])

    print(f"\n{'='*60}")
    print(f"FIX IMAGES PROPERLY - {len(articles)} matched articles")
    if images_only:
        print("Mode: IMAGES ONLY (add missing, preserve content)")
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

        if fix_article_images(
            article_id, pinterest_url, dry_run, images_only=images_only
        ):
            success += 1
        else:
            failed += 1

        # Rate limiting
        if not dry_run:
            time.sleep(2)

    print(f"\n{'='*60}")
    print(f"DONE: {success} success, {failed} failed")
    print(f"{'='*60}")
    return failed == 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fix article images properly")
    parser.add_argument("--article-id", type=int, help="Single article ID to fix")
    parser.add_argument(
        "--ids", help="Comma-separated article IDs (e.g. 690329256254,690329289022)"
    )
    parser.add_argument("--all", action="store_true", help="Fix all matched articles")
    parser.add_argument("--dry-run", action="store_true", help="Don't make changes")
    parser.add_argument(
        "--images-only",
        action="store_true",
        help="Only ADD missing images; do NOT remove or modify existing content",
    )
    args = parser.parse_args()

    if args.article_id:
        # Load matched data to get Pinterest URL (draft_id can be int or str)
        matched_data = load_matched_data()
        pinterest_url = None
        aid = args.article_id
        for article in matched_data.get("matched", []):
            did = article.get("draft_id")
            if did == aid or str(did) == str(aid):
                pin_id = article.get("pin_id", "") or article.get("pin_url", "")
                if pin_id and "pinimg.com" in str(pin_id):
                    pinterest_url = str(pin_id)
                elif pin_id:
                    pinterest_url = get_pinterest_image_url(str(pin_id))
                break

        ok = fix_article_images(
            args.article_id,
            pinterest_url,
            args.dry_run,
            images_only=args.images_only,
        )
        sys.exit(0 if ok else 1)
    elif args.ids:
        ids = [x.strip() for x in args.ids.split(",") if x.strip()]
        matched_data = load_matched_data()
        success, failed = 0, 0
        for aid in ids:
            try:
                aid_int = int(aid)
            except ValueError:
                continue
            pinterest_url = None
            for m in matched_data.get("matched", []):
                did = m.get("draft_id")
                if did == aid_int or str(did) == str(aid):
                    pin_id = m.get("pin_id") or m.get("pin_url")
                    if pin_id and "pinimg.com" in str(pin_id):
                        pinterest_url = str(pin_id)
                    elif pin_id:
                        pinterest_url = get_pinterest_image_url(str(pin_id))
                    break
            if fix_article_images(
                aid_int, pinterest_url, args.dry_run, images_only=args.images_only
            ):
                success += 1
            else:
                failed += 1
            if not args.dry_run:
                time.sleep(2)
        print(f"\nDONE: {success} success, {failed} failed")
        sys.exit(0 if failed == 0 else 1)
    elif args.all:
        ok = fix_all_matched_articles(args.dry_run, images_only=args.images_only)
        sys.exit(0 if ok else 1)
    else:
        print(
            "Usage: python fix_images_properly.py --article-id ID [--images-only] [--dry-run]"
        )
        print(
            "       python fix_images_properly.py --ids ID1,ID2,... [--images-only] [--dry-run]"
        )
        print("       python fix_images_properly.py --all [--images-only] [--dry-run]")
