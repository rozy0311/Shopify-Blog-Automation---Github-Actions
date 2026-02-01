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

url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/articles/690495095102.json"
data = {"article": {"id": 690495095102, "published": True}}
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
