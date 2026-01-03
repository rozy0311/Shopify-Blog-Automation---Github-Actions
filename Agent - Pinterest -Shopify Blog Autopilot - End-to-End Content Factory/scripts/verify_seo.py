"""
Verify article SEO fields via Shopify API
"""

import requests
import json
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"

config = json.loads(CONFIG_PATH.read_text())
shop = config["shop"]

headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": shop["access_token"],
}

ARTICLE_ID = 690495095102

# Check via REST API
rest_url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/articles/{ARTICLE_ID}.json"
resp = requests.get(rest_url, headers=headers)
article = resp.json().get("article", {})

print("=" * 60)
print("ARTICLE DETAILS (REST API)")
print("=" * 60)
print(f"Title: {article.get('title')}")
print(f"Author: {article.get('author')}")
print(f"Handle: {article.get('handle')}")
print(f"Published: {article.get('published_at')}")
print(
    f"Image: {article.get('image', {}).get('src', 'None')[:60] if article.get('image') else 'None'}..."
)
print(f"Body length: {len(article.get('body_html', ''))}")

# Check metafields
print("\n" + "=" * 60)
print("METAFIELDS")
print("=" * 60)

metafields_url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/articles/{ARTICLE_ID}/metafields.json"
resp = requests.get(metafields_url, headers=headers)
metafields = resp.json().get("metafields", [])

if metafields:
    for mf in metafields:
        print(f"  {mf.get('namespace')}.{mf.get('key')}: {mf.get('value', '')[:50]}...")
else:
    print("  No metafields found")

# Try to set SEO via metafields API
print("\n" + "=" * 60)
print("SETTING SEO VIA METAFIELDS API")
print("=" * 60)

seo_title = "How to Make Homemade Vinegar from Fruit Scraps | DIY Guide"
seo_desc = "Learn how to make homemade vinegar from fruit scraps in 3-4 weeks. Step-by-step guide with troubleshooting tips. Zero waste and all-natural!"

# Create SEO title metafield
metafield_data = {
    "metafield": {
        "namespace": "global",
        "key": "title_tag",
        "value": seo_title,
        "type": "single_line_text_field",
    }
}

resp = requests.post(metafields_url, headers=headers, json=metafield_data)
print(f"Title metafield: {resp.status_code}")
if resp.status_code not in [200, 201]:
    print(f"  Error: {resp.text[:200]}")

# Create SEO description metafield
metafield_data = {
    "metafield": {
        "namespace": "global",
        "key": "description_tag",
        "value": seo_desc,
        "type": "single_line_text_field",
    }
}

resp = requests.post(metafields_url, headers=headers, json=metafield_data)
print(f"Description metafield: {resp.status_code}")
if resp.status_code not in [200, 201]:
    print(f"  Error: {resp.text[:200]}")

# Verify again
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)

resp = requests.get(metafields_url, headers=headers)
metafields = resp.json().get("metafields", [])

if metafields:
    for mf in metafields:
        print(
            f"  ✅ {mf.get('namespace')}.{mf.get('key')}: {mf.get('value', '')[:60]}..."
        )
else:
    print("  No metafields found")

print(
    f"\n🔗 Admin: https://admin.shopify.com/store/therikeus/content/articles/{ARTICLE_ID}"
)
print(
    f"🌐 Live: https://the-rike-inc.myshopify.com/blogs/sustainable-living/how-to-make-homemade-vinegar-from-fruit-scraps"
)
