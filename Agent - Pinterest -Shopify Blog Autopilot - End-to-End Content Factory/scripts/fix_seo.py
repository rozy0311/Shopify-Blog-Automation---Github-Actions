"""
Fix article SEO - Add author, SEO title, meta description
"""

import requests
import json
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"

# Shopify config
config = json.loads(CONFIG_PATH.read_text())
shop = config["shop"]
url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/graphql.json"
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": shop["access_token"],
}

ARTICLE_ID = "gid://shopify/Article/690495095102"
ARTICLE_ID_NUM = 690495095102

# Get article info via REST API
rest_url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/articles/{ARTICLE_ID_NUM}.json"

resp = requests.get(rest_url, headers=headers)
if resp.status_code != 200:
    print(f"Error getting article: {resp.status_code}")
    print(resp.text)
    exit(1)

data = resp.json()
article = data["article"]

print("=" * 60)
print("FIX ARTICLE SEO")
print("=" * 60)
print(f"\n📄 Article: {article['title']}")
print(f"   Handle: {article.get('handle', 'N/A')}")
print(f"   Current author: {article.get('author', 'Not set')}")
print(f"   Current SEO title: {article.get('metafields_global_title_tag', 'Not set')}")
print(
    f"   Current SEO desc: {str(article.get('metafields_global_description_tag', 'Not set'))[:50]}..."
)

# Generate SEO content
title = article["title"]  # "How to Make Homemade Vinegar from Fruit Scraps"

# SEO title: 50-60 chars, include main keyword
seo_title = "How to Make Homemade Vinegar from Fruit Scraps | Easy DIY Guide"
if len(seo_title) > 60:
    seo_title = seo_title[:57] + "..."

# Meta description: 150-160 chars, include keywords, call to action
seo_description = (
    "Learn how to make homemade vinegar from fruit scraps in 3-4 weeks. "
    "Step-by-step guide with troubleshooting tips. Zero waste, all-natural, free! "
    "Transform kitchen scraps into useful vinegar."
)
if len(seo_description) > 160:
    seo_description = seo_description[:157] + "..."

print(f"\n📝 New SEO settings:")
print(f"   Author: The Rike")
print(f"   SEO Title ({len(seo_title)} chars): {seo_title}")
print(f"   Meta Desc ({len(seo_description)} chars): {seo_description[:60]}...")

# Update via REST API (GraphQL has issues with author)
rest_url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/articles/690495095102.json"
rest_headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": shop["access_token"],
}

article_update = {
    "article": {
        "id": 690495095102,
        "author": "The Rike",
        "metafields_global_title_tag": seo_title,
        "metafields_global_description_tag": seo_description,
    }
}

resp = requests.put(rest_url, headers=rest_headers, json=article_update)

if resp.status_code == 200:
    result = resp.json()
    updated = result.get("article", {})
    print(f"\n✅ Article updated!")
    print(f"   Author: {updated.get('author', 'Not set')}")
    print(f"   Published: {updated.get('published_at', 'Not set')}")
else:
    print(f"\n❌ Error: {resp.status_code}")
    print(f"   {resp.text[:500]}")

# Verify with REST API
resp = requests.get(rest_url, headers=headers)
if resp.status_code == 200:
    data = resp.json()
    article = data["article"]

    print(f"\n🔍 Verification:")
    print(f"   Author: {article.get('author', 'Not set')}")
    print(f"   Title: {article.get('title', 'Not set')}")
else:
    print(f"\n⚠️ Could not verify: {resp.status_code}")

print(
    f"\n🔗 Admin: https://admin.shopify.com/store/therikeus/content/articles/690495095102"
)
