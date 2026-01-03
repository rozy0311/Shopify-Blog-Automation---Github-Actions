"""
Fix article images v2 - Find UNIQUE images and set featured image

Issues fixed:
1. First 3 images were identical - now ensures all unique
2. Missing main/featured image - now sets article image
3. Missing alt text - now adds SEO-friendly alt text
4. Images with unclear text - filters out images with text overlays
"""

import requests
import json
import re
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"
CONTENT_DIR = ROOT_DIR / "content"

# Shopify config
config = json.loads(CONFIG_PATH.read_text())
shop = config["shop"]
url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/graphql.json"
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": shop["access_token"],
}

# Pexels API
PEXELS_API_KEY = os.environ.get(
    "PEXELS_API_KEY", "os.environ.get("PEXELS_API_KEY", "")"
)


def search_pexels_diverse(queries: list, per_page: int = 10) -> list:
    """Search Pexels with multiple queries to get diverse images."""
    if not PEXELS_API_KEY:
        print("❌ PEXELS_API_KEY not set")
        return []

    all_images = []
    seen_ids = set()

    pexels_headers = {"Authorization": PEXELS_API_KEY}

    for query in queries:
        print(f"\n🔍 Searching: '{query}'")
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": "landscape",
        }

        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                headers=pexels_headers,
                params=params,
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                for photo in data.get("photos", []):
                    photo_id = photo["id"]

                    # Skip duplicates
                    if photo_id in seen_ids:
                        continue
                    seen_ids.add(photo_id)

                    # Get alt text from Pexels
                    alt = photo.get("alt", "")

                    # Skip images with potential unclear text (very short alt = likely has text overlay)
                    # Also skip if alt mentions "text", "quote", "banner", etc.
                    skip_words = [
                        "text",
                        "quote",
                        "banner",
                        "sign",
                        "poster",
                        "letter",
                        "word",
                        "font",
                    ]
                    if any(word in alt.lower() for word in skip_words):
                        print(f"  ⏭️  Skipping {photo_id} - has text: {alt[:50]}")
                        continue

                    # Only high quality images
                    if photo["width"] < 800 or photo["height"] < 500:
                        continue

                    image_data = {
                        "id": photo_id,
                        "url": photo["src"]["large2x"],  # Higher quality
                        "url_medium": photo["src"]["large"],
                        "photographer": photo.get("photographer", "Unknown"),
                        "alt_original": alt,
                        "width": photo["width"],
                        "height": photo["height"],
                        "query": query,
                    }

                    all_images.append(image_data)
                    print(f"  ✅ Found: {photo_id} - {alt[:40]}...")

            else:
                print(f"  ❌ Error {resp.status_code}: {resp.text[:100]}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    return all_images


def generate_seo_alt_text(image: dict, topic: str, position: str) -> str:
    """Generate SEO-friendly alt text."""
    original_alt = image.get("alt_original", "")
    query = image.get("query", "")

    # Clean topic for alt text
    topic_clean = topic.lower().replace("how to make ", "").replace("homemade ", "")

    # Position-specific prefixes
    prefixes = {
        "hero": f"Featured image: {topic}",
        "section1": f"{topic_clean.title()} preparation",
        "section2": f"Making {topic_clean}",
        "section3": f"{topic_clean.title()} ingredients and supplies",
        "section4": f"Finished {topic_clean} in glass jar",
    }

    base = prefixes.get(position, topic)

    # Add description from original alt if useful
    if original_alt and len(original_alt) > 20:
        # Clean up Pexels alt text
        desc = original_alt.replace("Photo of ", "").replace("photo of ", "")
        desc = desc[:80]
        return f"{base} - {desc}"

    return base


def upload_image_to_shopify(image_url: str, alt_text: str) -> dict:
    """Upload image to Shopify Files and get permanent URL."""

    # Step 1: Create staged upload
    stage_mutation = """
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

    stage_vars = {
        "input": [
            {
                "filename": f"article-image-{alt_text[:20].replace(' ', '-')}.jpg",
                "mimeType": "image/jpeg",
                "resource": "FILE",
                "httpMethod": "POST",
            }
        ]
    }

    resp = requests.post(
        url, headers=headers, json={"query": stage_mutation, "variables": stage_vars}
    )
    data = resp.json()

    targets = (
        data.get("data", {}).get("stagedUploadsCreate", {}).get("stagedTargets", [])
    )
    if not targets:
        print(f"  ❌ Failed to create staged upload")
        return None

    target = targets[0]
    upload_url = target["url"]
    resource_url = target["resourceUrl"]
    params = {p["name"]: p["value"] for p in target["parameters"]}

    # Step 2: Download image from Pexels
    img_resp = requests.get(image_url, timeout=30)
    if img_resp.status_code != 200:
        print(f"  ❌ Failed to download image")
        return None

    # Step 3: Upload to staged target
    files = {"file": ("image.jpg", img_resp.content, "image/jpeg")}
    upload_resp = requests.post(upload_url, data=params, files=files, timeout=60)

    if upload_resp.status_code not in [200, 201, 204]:
        print(f"  ❌ Upload failed: {upload_resp.status_code}")
        return None

    # Step 4: Create file in Shopify
    file_mutation = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files {
          id
          alt
          ... on MediaImage {
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

    file_vars = {
        "files": [
            {
                "originalSource": resource_url,
                "alt": alt_text,
                "contentType": "IMAGE",
            }
        ]
    }

    resp = requests.post(
        url, headers=headers, json={"query": file_mutation, "variables": file_vars}
    )
    result = resp.json()

    files_created = result.get("data", {}).get("fileCreate", {}).get("files", [])
    if files_created:
        file_info = files_created[0]
        image_obj = file_info.get("image") or {}
        return {
            "id": file_info.get("id"),
            "url": image_obj.get("url", resource_url),
            "alt": alt_text,
        }

    return None


def main():
    print("=" * 60)
    print("FIX IMAGES V2 - Unique Images + Featured Image + Alt Text")
    print("=" * 60)

    # Define diverse search queries for homemade vinegar topic
    queries = [
        "homemade fruit vinegar glass jar",
        "apple cider vinegar making process",
        "fermentation jar kitchen",
        "fruit scraps compost sustainable",
        "glass jar preserves pantry",
        "organic apple vinegar wooden table",
        "kitchen fermenting vegetables",
    ]

    # Search for diverse images
    images = search_pexels_diverse(queries, per_page=5)
    print(f"\n📷 Found {len(images)} unique images total")

    if len(images) < 5:
        print("❌ Not enough unique images found")
        return

    # Select 5 best images (1 hero + 4 sections)
    selected = images[:5]

    print("\n" + "=" * 60)
    print("SELECTED IMAGES:")
    print("=" * 60)

    topic = "How to Make Homemade Vinegar from Fruit Scraps"
    positions = ["hero", "section1", "section2", "section3", "section4"]

    final_images = []
    for i, (img, pos) in enumerate(zip(selected, positions)):
        alt_text = generate_seo_alt_text(img, topic, pos)
        print(f"\n{i+1}. {pos.upper()}")
        print(f"   ID: {img['id']}")
        print(f"   Query: {img['query']}")
        print(f"   Alt: {alt_text}")

        final_images.append(
            {
                "url": img["url"],
                "url_medium": img["url_medium"],
                "alt": alt_text,
                "photographer": img["photographer"],
                "position": pos,
            }
        )

    # Get current article
    query = """
    query {
      article(id: "gid://shopify/Article/690495095102") {
        id
        title
        body
        image {
          url
        }
      }
    }
    """

    resp = requests.post(url, headers=headers, json={"query": query})
    data = resp.json()
    article = data["data"]["article"]
    body = article["body"]

    print(f"\n📄 Article: {article['title']}")
    print(f"   Current body length: {len(body)}")
    print(f"   Has featured image: {bool(article.get('image'))}")

    # Remove old figure/img tags
    body = re.sub(
        r'<figure class="article-hero-image">.*?</figure>\s*', "", body, flags=re.DOTALL
    )
    body = re.sub(
        r'<figure class="article-section-image"[^>]*>.*?</figure>\s*',
        "",
        body,
        flags=re.DOTALL,
    )

    print(f"   Body after cleanup: {len(body)}")

    # Insert hero image after first paragraph
    hero = final_images[0]
    hero_html = f"""
<figure class="article-hero-image" style="margin:24px 0;">
  <img src="{hero['url']}"
       alt="{hero['alt']}"
       loading="eager"
       width="1260"
       height="750"
       style="width:100%;height:auto;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
  <figcaption style="text-align:center;font-size:0.85em;color:#666;margin-top:10px;">
    {hero['alt']} | Photo by {hero['photographer']} via Pexels
  </figcaption>
</figure>
"""

    first_p = body.find("</p>")
    if first_p > 0:
        body = body[: first_p + 4] + hero_html + body[first_p + 4 :]

    # Insert section images after h2 headings
    h2_pattern = re.compile(r"(</h2>)")
    matches = list(h2_pattern.finditer(body))

    offset = 0
    section_images = final_images[1:]  # Skip hero

    for i, match in enumerate(matches[: len(section_images)]):
        img = section_images[i]
        img_html = f"""
<figure class="article-section-image" style="margin:24px 0;">
  <img src="{img['url']}"
       alt="{img['alt']}"
       loading="lazy"
       width="1260"
       height="750"
       style="width:100%;height:auto;border-radius:8px;">
  <figcaption style="text-align:center;font-size:0.8em;color:#888;margin-top:8px;">
    {img['alt']}
  </figcaption>
</figure>
"""
        insert_pos = match.end() + offset
        body = body[:insert_pos] + img_html + body[insert_pos:]
        offset += len(img_html)

    print(f"\n   New body length: {len(body)}")
    print(f"   Images inserted: {len(final_images)}")

    # Upload hero image to Shopify for featured image
    print("\n📤 Uploading hero image to Shopify Files...")
    uploaded = upload_image_to_shopify(hero["url"], hero["alt"])

    # Update article with body and featured image
    mutation = """
    mutation articleUpdate($id: ID!, $article: ArticleUpdateInput!) {
      articleUpdate(id: $id, article: $article) {
        article {
          id
          title
          image {
            url
          }
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    article_update = {"body": body}

    # Set featured image if upload succeeded
    if uploaded and uploaded.get("url"):
        article_update["image"] = {
            "src": uploaded["url"],
            "altText": hero["alt"],
        }
        print(f"   ✅ Featured image URL: {uploaded['url'][:60]}...")
    else:
        # Use direct Pexels URL as fallback
        article_update["image"] = {
            "src": hero["url"],
            "altText": hero["alt"],
        }
        print(f"   ⚠️ Using Pexels URL directly for featured image")

    variables = {"id": "gid://shopify/Article/690495095102", "article": article_update}

    resp = requests.post(
        url, headers=headers, json={"query": mutation, "variables": variables}
    )
    result = resp.json()

    if result.get("data", {}).get("articleUpdate", {}).get("article"):
        updated = result["data"]["articleUpdate"]["article"]
        print("\n" + "=" * 60)
        print("✅ ARTICLE UPDATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Title: {updated['title']}")
        print(
            f"Featured image: {updated.get('image', {}).get('url', 'Not set')[:60]}..."
        )
        print(
            f"\n🔗 Admin: https://admin.shopify.com/store/therikeus/content/articles/690495095102"
        )
        print(
            f"🌐 Live: https://the-rike-inc.myshopify.com/blogs/sustainable-living/how-to-make-homemade-vinegar-from-fruit-scraps"
        )
    else:
        errors = result.get("data", {}).get("articleUpdate", {}).get("userErrors", [])
        print(f"\n❌ Error updating article: {errors}")
        print(f"Full response: {json.dumps(result, indent=2)}")

    # Save image review for reference
    review_data = {
        "topic": topic,
        "images": final_images,
        "featured_image": hero,
    }
    review_path = CONTENT_DIR / "image_review_v2.json"
    review_path.write_text(json.dumps(review_data, indent=2, ensure_ascii=False))
    print(f"\n📝 Review saved: {review_path}")


if __name__ == "__main__":
    main()
