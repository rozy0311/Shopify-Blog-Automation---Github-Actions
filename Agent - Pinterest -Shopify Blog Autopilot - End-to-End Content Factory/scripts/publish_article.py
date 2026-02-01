"""
Publish article with images to Shopify
"""

import requests
import json
import re

# Config
SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
API_VERSION = "2025-01"
BLOG_ID = "108441862462"

headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}

# Load article payload
with open("../content/article_payload.json", "r", encoding="utf-8-sig") as f:
    raw_payload = json.load(f)

# Handle both wrapped and unwrapped format
if "article" in raw_payload:
    payload = raw_payload["article"]
else:
    payload = raw_payload

# Load images
with open("../content/images.json", "r", encoding="utf-8") as f:
    images = json.load(f)

print(f"Title: {payload['title']}")
print(f"Images found: {len(images)}")

# Insert images into body_html
body_html = payload["body_html"]

# Find all h2 headings to insert images after them
h2_pattern = r"(<h2[^>]*>.*?</h2>)"
h2_matches = list(re.finditer(h2_pattern, body_html, re.IGNORECASE | re.DOTALL))

print(f"Found {len(h2_matches)} h2 headings")

# Insert images after specific h2 sections
insert_points = []
for i, match in enumerate(h2_matches[:5]):  # Max 5 images
    if i < len(images):
        insert_points.append((match.end(), images[i]))

# Insert from end to start to preserve positions
for pos, img in sorted(insert_points, reverse=True):
    alt = img.get("alt", "Vanilla extract making process")[:100]
    img_html = f'\n<figure><img src="{img["url"]}" alt="{alt}" loading="lazy" /><figcaption>Photo by {img["photographer"]} on Pexels</figcaption></figure>\n'
    body_html = body_html[:pos] + img_html + body_html[pos:]

# Create article
# Generate handle from title if not provided
import re as re_handle


def generate_handle(title):
    handle = title.lower()
    handle = re_handle.sub(r"[^a-z0-9\s-]", "", handle)
    handle = re_handle.sub(r"\s+", "-", handle)
    handle = re_handle.sub(r"-+", "-", handle)
    return handle.strip("-")


article_data = {
    "article": {
        "title": payload["title"],
        "author": payload.get("author", payload.get("author_name", "The Rike")),
        "body_html": body_html,
        "summary_html": payload.get("summary_html", payload.get("summary", "")),
        "tags": payload.get("tags", ""),
        "handle": payload.get("handle", generate_handle(payload["title"])),
        "published": True,
        "image": {
            "src": images[0]["url"],
            "alt": images[0].get("alt", payload["title"])[:100],
        },
    }
}

print("\nCreating article...")
url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles.json"
response = requests.post(url, headers=headers, json=article_data)

if response.status_code == 201:
    article = response.json()["article"]
    article_id = article["id"]
    print(f"✅ Article created! ID: {article_id}")
    print(f"   Handle: {article['handle']}")
    print(f"   Published: {article['published_at']}")

    # Set SEO metafields
    print("\nSetting SEO metafields...")
    metafields_url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/articles/{article_id}/metafields.json"

    # SEO Title
    seo_title = payload.get("seo_title", payload["title"])
    meta_data = {
        "metafield": {
            "namespace": "global",
            "key": "title_tag",
            "value": seo_title,
            "type": "single_line_text_field",
        }
    }
    r = requests.post(metafields_url, headers=headers, json=meta_data)
    print(f"   SEO Title: {'✅' if r.ok else '❌'}")

    # Meta Description
    meta_desc = payload.get("meta_desc", payload.get("summary_html", "")[:160])
    meta_data = {
        "metafield": {
            "namespace": "global",
            "key": "description_tag",
            "value": meta_desc,
            "type": "single_line_text_field",
        }
    }
    r = requests.post(metafields_url, headers=headers, json=meta_data)
    print(f"   Meta Desc: {'✅' if r.ok else '❌'}")

    print(f"\n🎉 Article published successfully!")
    print(
        f"   URL: https://the-rike-inc.myshopify.com/blogs/sustainable-living/{article['handle']}"
    )

    # Save result
    with open("../content/last_published.json", "w") as f:
        json.dump(
            {
                "article_id": article_id,
                "title": payload["title"],
                "handle": article["handle"],
                "published_at": article["published_at"],
            },
            f,
            indent=2,
        )
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
