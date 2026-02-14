"""Publish article"""

import requests
import json
from pathlib import Path

config = json.loads(
    Path(__file__).parent.parent.joinpath("SHOPIFY_PUBLISH_CONFIG.json").read_text()
)
shop = config["shop"]
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": shop["access_token"],
}

article_id = 690495095102
url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/articles/{article_id}.json"

# Guard: skip if already published to avoid resetting published_at
check = requests.get(url, headers=headers, timeout=30)
if check.status_code == 200:
    existing_pub = check.json().get("article", {}).get("published_at")
    if existing_pub:
        print(f"[SKIP] Already published at {existing_pub} — no re-publish.")
        raise SystemExit(0)

data = {"article": {"id": article_id, "published": True}}
resp = requests.put(url, headers=headers, json=data)
result = resp.json()
article = result.get("article", {})

print(f"Status: {resp.status_code}")
print(f"Title: {article.get('title')}")
print(f"Author: {article.get('author')}")
print(f"Published: {article.get('published_at')}")
print(
    f"Image: {article.get('image', {}).get('src', 'None')[:50] if article.get('image') else 'None'}..."
)
print(
    f"\n🌐 Live: https://the-rike-inc.myshopify.com/blogs/sustainable-living/{article.get('handle')}"
)
