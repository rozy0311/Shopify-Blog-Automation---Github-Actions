"""
Upload Approved Images to Shopify Article

This script:
1. Reads approved images from image_review.json
2. Downloads images locally
3. Uploads to Shopify Files API
4. Updates article HTML with image tags
5. Updates article via GraphQL

Usage:
    python scripts/upload_images_to_article.py <article_id>

Example:
    python scripts/upload_images_to_article.py 690495095102
"""

import json
import os
import sys
import re
import base64
import time
from pathlib import Path
from typing import Optional
import hashlib

try:
    import requests
except ImportError:
    os.system("pip install requests")
    import requests

# Paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = ROOT_DIR / "content"
CONFIG_PATH = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"
IMAGE_REVIEW_PATH = CONTENT_DIR / "image_review.json"
ARTICLE_PAYLOAD_PATH = CONTENT_DIR / "article_payload.json"
IMAGES_DIR = CONTENT_DIR / "images"


def load_config() -> dict:
    """Load Shopify config."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def load_image_review() -> dict:
    """Load approved images from review."""
    if IMAGE_REVIEW_PATH.exists():
        return json.loads(IMAGE_REVIEW_PATH.read_text(encoding="utf-8"))
    return {}


def load_article_payload() -> dict:
    """Load article payload."""
    if ARTICLE_PAYLOAD_PATH.exists():
        return json.loads(ARTICLE_PAYLOAD_PATH.read_text(encoding="utf-8"))
    return {}


def download_image(url: str, filename: str) -> Optional[Path]:
    """Download image to local folder."""
    IMAGES_DIR.mkdir(exist_ok=True)

    filepath = IMAGES_DIR / filename

    try:
        resp = requests.get(url, timeout=30, stream=True)
        if resp.status_code == 200:
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"  ✅ Downloaded: {filename}")
            return filepath
    except Exception as e:
        print(f"  ❌ Download failed: {e}")

    return None


def upload_to_shopify_files(filepath: Path, config: dict) -> Optional[str]:
    """Upload image to Shopify Files via staged uploads."""
    shop = config.get("shop", {})
    domain = shop.get("domain", "")
    token = shop.get("access_token", "")
    api_version = shop.get("api_version", "2025-10")

    if not domain or not token:
        print("ERROR: Missing Shopify credentials")
        return None

    url = f"https://{domain}/admin/api/{api_version}/graphql.json"
    headers = {"Content-Type": "application/json", "X-Shopify-Access-Token": token}

    # Read file
    file_data = filepath.read_bytes()
    file_size = len(file_data)
    filename = filepath.name

    # Determine MIME type
    ext = filepath.suffix.lower()
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime_type = mime_types.get(ext, "image/jpeg")

    # Step 1: Create staged upload
    staged_mutation = """
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
                "resource": "FILE",
                "filename": filename,
                "mimeType": mime_type,
                "fileSize": str(file_size),
                "httpMethod": "POST",
            }
        ]
    }

    resp = requests.post(
        url, headers=headers, json={"query": staged_mutation, "variables": variables}
    )
    if resp.status_code != 200:
        print(f"  ❌ Staged upload failed: {resp.status_code}")
        return None

    data = resp.json()
    staged = data.get("data", {}).get("stagedUploadsCreate", {})

    if staged.get("userErrors"):
        print(f"  ❌ Staged upload errors: {staged['userErrors']}")
        return None

    targets = staged.get("stagedTargets", [])
    if not targets:
        print("  ❌ No staged targets returned")
        return None

    target = targets[0]
    upload_url = target["url"]
    resource_url = target["resourceUrl"]
    params = {p["name"]: p["value"] for p in target["parameters"]}

    # Step 2: Upload file to staged URL
    files = {"file": (filename, file_data, mime_type)}
    upload_resp = requests.post(upload_url, data=params, files=files, timeout=60)

    if upload_resp.status_code not in [200, 201, 204]:
        print(f"  ❌ File upload failed: {upload_resp.status_code}")
        return None

    # Step 3: Create file in Shopify
    file_create_mutation = """
    mutation fileCreate($files: [FileCreateInput!]!) {
      fileCreate(files: $files) {
        files {
          ... on MediaImage {
            id
            image {
              url
              altText
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

    file_variables = {
        "files": [{"originalSource": resource_url, "contentType": "IMAGE"}]
    }

    file_resp = requests.post(
        url,
        headers=headers,
        json={"query": file_create_mutation, "variables": file_variables},
    )
    if file_resp.status_code != 200:
        print(f"  ❌ File create failed: {file_resp.status_code}")
        return None

    file_data = file_resp.json()
    files_created = file_data.get("data", {}).get("fileCreate", {}).get("files", [])

    if files_created and files_created[0] is not None:
        image_data = files_created[0].get("image") or {}
        image_url = image_data.get("url", "")
        if image_url:
            print(f"  ✅ Uploaded to Shopify: {image_url[:60]}...")
            return image_url

    # Check for user errors
    user_errors = file_data.get("data", {}).get("fileCreate", {}).get("userErrors", [])
    if user_errors:
        print(f"  ⚠️ File create warnings: {user_errors}")

    # Fallback: return resource URL (staged upload URL works as CDN)
    print(f"  ⚠️ Using staged URL: {resource_url[:60]}...")
    return resource_url


def insert_images_into_html(body_html: str, images: list, topic: str) -> str:
    """Insert approved images into article HTML."""
    if not images:
        return body_html

    # First image becomes hero (before first h2)
    hero_image = images[0]
    hero_html = f"""
<figure class="article-hero-image">
  <img src="{hero_image['shopify_url']}"
       alt="{hero_image['alt_text']}"
       loading="eager"
       width="{hero_image.get('width', 1200)}"
       height="{hero_image.get('height', 800)}">
  <figcaption>Photo by {hero_image['photographer']} via {hero_image['source'].title()}</figcaption>
</figure>
"""

    # Insert hero after first paragraph or intro
    first_p_end = body_html.find("</p>")
    if first_p_end > 0:
        body_html = (
            body_html[: first_p_end + 4] + hero_html + body_html[first_p_end + 4 :]
        )
    else:
        body_html = hero_html + body_html

    # Insert remaining images after h2 sections
    h2_pattern = re.compile(r"(</h2>)")
    h2_matches = list(h2_pattern.finditer(body_html))

    # Insert images after h2 headings (max 1 per section)
    inserted = 0
    offset = 0

    for i, match in enumerate(h2_matches):
        if i + 1 >= len(images):
            break

        img = images[i + 1]
        img_html = f"""
<figure class="article-section-image">
  <img src="{img['shopify_url']}"
       alt="{img['alt_text']}"
       loading="lazy"
       width="{img.get('width', 800)}"
       height="{img.get('height', 600)}">
</figure>
"""
        insert_pos = match.end() + offset
        body_html = body_html[:insert_pos] + img_html + body_html[insert_pos:]
        offset += len(img_html)
        inserted += 1

    print(f"  Inserted {inserted + 1} images into HTML")
    return body_html


def update_article_with_images(article_id: str, body_html: str, config: dict) -> bool:
    """Update article HTML with images via GraphQL."""
    shop = config.get("shop", {})
    domain = shop.get("domain", "")
    token = shop.get("access_token", "")
    api_version = shop.get("api_version", "2025-10")

    url = f"https://{domain}/admin/api/{api_version}/graphql.json"
    headers = {"Content-Type": "application/json", "X-Shopify-Access-Token": token}

    # Format article GID
    if not article_id.startswith("gid://"):
        article_gid = f"gid://shopify/Article/{article_id}"
    else:
        article_gid = article_id

    mutation = """
    mutation articleUpdate($id: ID!, $article: ArticleUpdateInput!) {
      articleUpdate(id: $id, article: $article) {
        article {
          id
          title
        }
        userErrors {
          field
          message
        }
      }
    }
    """

    variables = {"id": article_gid, "article": {"body": body_html}}

    resp = requests.post(
        url, headers=headers, json={"query": mutation, "variables": variables}
    )

    if resp.status_code != 200:
        print(f"  ❌ Update failed: {resp.status_code}")
        return False

    data = resp.json()
    result = data.get("data", {}).get("articleUpdate", {})

    if result.get("userErrors"):
        print(f"  ❌ Update errors: {result['userErrors']}")
        return False

    if result.get("article"):
        print(f"  ✅ Article updated: {result['article']['title']}")
        return True

    return False


def main(article_id: str):
    """Main entry point."""
    print(f"\n{'='*60}")
    print("UPLOAD IMAGES TO SHOPIFY ARTICLE")
    print(f"{'='*60}")
    print(f"Article ID: {article_id}")

    # Load config
    config = load_config()
    if not config:
        print("ERROR: No config found")
        sys.exit(1)

    # Load image review
    review = load_image_review()
    if not review or not review.get("approved_images"):
        print("ERROR: No approved images found")
        print("Run image_review_agent.py first")
        sys.exit(1)

    approved_images = review["approved_images"]
    print(f"Found {len(approved_images)} approved images")

    # Load article payload
    article = load_article_payload()
    if not article:
        print("ERROR: No article payload found")
        sys.exit(1)

    # Download and upload each image
    print(f"\n--- Downloading & Uploading Images ---")

    uploaded_images = []
    for i, img in enumerate(approved_images):
        print(f"\nImage {i+1}/{len(approved_images)}:")

        # Generate filename
        ext = ".jpg"
        if "png" in img["url"].lower():
            ext = ".png"
        elif "webp" in img["url"].lower():
            ext = ".webp"

        filename = f"article_{article_id}_{i+1}{ext}"

        # Download
        local_path = download_image(img["url"], filename)
        if not local_path:
            continue

        # Upload to Shopify
        shopify_url = upload_to_shopify_files(local_path, config)
        if shopify_url:
            img["shopify_url"] = shopify_url
            uploaded_images.append(img)

    if not uploaded_images:
        print("\n❌ No images uploaded successfully")
        sys.exit(1)

    print(f"\n✅ Uploaded {len(uploaded_images)} images to Shopify")

    # Insert images into HTML
    print(f"\n--- Inserting Images into Article ---")

    body_html = article.get("body_html", "")
    updated_html = insert_images_into_html(
        body_html, uploaded_images, article.get("title", "")
    )

    # Update article
    success = update_article_with_images(article_id, updated_html, config)

    if success:
        print(f"\n{'='*60}")
        print("✅ IMAGES ADDED TO ARTICLE SUCCESSFULLY")
        print(f"{'='*60}")

        # Save updated payload
        article["body_html"] = updated_html
        article["images_added"] = len(uploaded_images)
        ARTICLE_PAYLOAD_PATH.write_text(
            json.dumps(article, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    else:
        print(f"\n❌ Failed to update article")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/upload_images_to_article.py <article_id>")
        print("Example: python scripts/upload_images_to_article.py 690495095102")
        sys.exit(1)

    article_id = sys.argv[1]
    main(article_id)
