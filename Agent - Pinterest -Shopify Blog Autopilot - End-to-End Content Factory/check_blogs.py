import os
import requests
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOP = os.getenv("SHOPIFY_SHOP")

# Get all blogs
url = f"https://{SHOP}/admin/api/2025-01/blogs.json"
resp = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN})
print(f"Status: {resp.status_code}")
blogs = resp.json().get("blogs", [])
print(f"Found {len(blogs)} blogs:")
for b in blogs:
    print(f"  ID: {b['id']} - {b['title']}")

# Count articles per blog
for b in blogs:
    blog_id = b["id"]
    url = f"https://{SHOP}/admin/api/2025-01/blogs/{blog_id}/articles/count.json"
    resp = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN})
    count = resp.json().get("count", 0)
    print(f"  Blog {blog_id}: {count} articles")
