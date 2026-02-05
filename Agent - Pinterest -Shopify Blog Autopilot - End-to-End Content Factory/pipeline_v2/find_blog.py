import os
import requests
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

SHOP = os.getenv("SHOPIFY_SHOP")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
headers = {"X-Shopify-Access-Token": TOKEN}
resp = requests.get(f"https://{SHOP}/admin/api/2025-01/blogs.json", headers=headers)
blogs = resp.json().get("blogs", [])
for b in blogs:
    print(f"{b['id']}: {b['title']} ({b.get('articles_count', 0)} articles)")
