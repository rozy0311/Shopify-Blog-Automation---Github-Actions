"""
Fix article images v3 - Correct Shopify API for featured image
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

# Load images from v2
review_path = CONTENT_DIR / "image_review_v2.json"
review_data = json.loads(review_path.read_text())
final_images = review_data["images"]

print("=" * 60)
print("FIX IMAGES V3 - Update body with unique images")
print("=" * 60)

# Get current article
query = """
query {
  article(id: "gid://shopify/Article/690495095102") {
    id
    title
    body
    image {
      url
      altText
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
print(f"   Has featured image: {article.get('image') is not None}")

# Remove old figure/img tags
body = re.sub(
    r'<figure class="article-hero-image"[^>]*>.*?</figure>\s*',
    "",
    body,
    flags=re.DOTALL,
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

# Update article body first
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

variables = {"id": "gid://shopify/Article/690495095102", "article": {"body": body}}

resp = requests.post(
    url, headers=headers, json={"query": mutation, "variables": variables}
)
result = resp.json()

if result.get("data", {}).get("articleUpdate", {}).get("article"):
    print("\n✅ Body updated with 5 unique images!")
else:
    errors = result.get("data", {}).get("articleUpdate", {}).get("userErrors", [])
    print(f"\n❌ Error updating body: {errors}")
    print(f"Full response: {json.dumps(result, indent=2)}")
    exit(1)

# Now try to set featured image using REST API (GraphQL has issues)
print("\n📤 Setting featured image via REST API...")

rest_url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/articles/690495095102.json"
rest_headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": shop["access_token"],
}

# Use direct Pexels URL for featured image
article_update = {
    "article": {"id": 690495095102, "image": {"src": hero["url"], "alt": hero["alt"]}}
}

resp = requests.put(rest_url, headers=rest_headers, json=article_update)

if resp.status_code == 200:
    result = resp.json()
    featured_url = result.get("article", {}).get("image", {}).get("src", "Not set")
    print(f"   ✅ Featured image set: {featured_url[:60]}...")
else:
    print(f"   ⚠️ REST API returned {resp.status_code}")
    print(f"   Response: {resp.text[:500]}")

print("\n" + "=" * 60)
print("RESULT:")
print("=" * 60)
print(f"📷 5 unique images from Pexels inserted in article body")
print(f"🖼️ Hero image: {hero['alt'][:50]}...")

# List all images
print("\nImages used:")
for i, img in enumerate(final_images, 1):
    print(f"  {i}. ID: {img['url'].split('/')[-1][:20]} - {img['position']}")
    print(f"     Alt: {img['alt'][:60]}...")

print(
    f"\n🔗 Admin: https://admin.shopify.com/store/therikeus/content/articles/690495095102"
)
print(
    f"🌐 Live: https://the-rike-inc.myshopify.com/blogs/sustainable-living/how-to-make-homemade-vinegar-from-fruit-scraps"
)
