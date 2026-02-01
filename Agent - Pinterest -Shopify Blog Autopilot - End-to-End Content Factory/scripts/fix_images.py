"""
Fix article images - Use direct Pexels URLs instead of expired staged uploads
"""

import requests
import json
import re
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"
IMAGE_REVIEW_PATH = ROOT_DIR / "content" / "image_review.json"

config = json.loads(CONFIG_PATH.read_text())
shop = config["shop"]
url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/graphql.json"
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": shop["access_token"],
}

# Load approved images
review = json.loads(IMAGE_REVIEW_PATH.read_text())
approved = review["approved_images"]

# Get unique images (remove duplicates)
seen = set()
unique_images = []
for img in approved:
    if img["url"] not in seen:
        seen.add(img["url"])
        unique_images.append(img)

print(f"Unique images: {len(unique_images)}")

# Get current article
query = """
query {
  article(id: "gid://shopify/Article/690495095102") {
    id
    title
    body
  }
}
"""

resp = requests.post(url, headers=headers, json={"query": query})
data = resp.json()
article = data["data"]["article"]
body = article["body"]

print(f"Article: {article['title']}")
print(f"Current body length: {len(body)}")

# Remove old figure/img tags with staged URLs
body = re.sub(
    r'<figure class="article-hero-image">.*?</figure>\s*', "", body, flags=re.DOTALL
)
body = re.sub(
    r'<figure class="article-section-image">.*?</figure>\s*', "", body, flags=re.DOTALL
)

print(f"Body after removing old images: {len(body)}")

# Insert new images with direct Pexels URLs
if unique_images:
    # Hero image after first paragraph
    hero = unique_images[0]
    hero_html = f"""
<figure class="article-hero-image">
  <img src="{hero['url']}"
       alt="{hero['alt_text']}"
       loading="eager"
       width="940"
       height="627"
       style="width:100%;height:auto;border-radius:8px;">
  <figcaption style="text-align:center;font-size:0.9em;color:#666;margin-top:8px;">Photo by {hero['photographer']} via Pexels</figcaption>
</figure>
"""

    # Insert after first </p>
    first_p = body.find("</p>")
    if first_p > 0:
        body = body[: first_p + 4] + hero_html + body[first_p + 4 :]

    # Section images after h2
    h2_pattern = re.compile(r"(</h2>)")
    matches = list(h2_pattern.finditer(body))

    offset = 0
    for i, match in enumerate(matches[: len(unique_images) - 1]):
        if i + 1 >= len(unique_images):
            break

        img = unique_images[i + 1]
        img_html = f"""
<figure class="article-section-image" style="margin:24px 0;">
  <img src="{img['url']}"
       alt="{img['alt_text']}"
       loading="lazy"
       width="940"
       height="627"
       style="width:100%;height:auto;border-radius:8px;">
</figure>
"""
        insert_pos = match.end() + offset
        body = body[:insert_pos] + img_html + body[insert_pos:]
        offset += len(img_html)

print(f"New body length: {len(body)}")
print(f"Images inserted: {len(unique_images)}")

# Update article
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
    print("\n✅ Article updated with Pexels image URLs!")
    print(
        "Check: https://admin.shopify.com/store/therikeus/content/articles/690495095102"
    )
else:
    print(f"\n❌ Error: {result}")
