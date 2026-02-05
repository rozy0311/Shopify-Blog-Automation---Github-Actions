import os
import requests
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

SHOP = os.getenv("SHOPIFY_SHOP")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

# Get all blogs
url = f"https://{SHOP}/admin/api/2025-01/blogs.json"
headers = {"X-Shopify-Access-Token": TOKEN}
r = requests.get(url, headers=headers)
if r.status_code == 200:
    blogs = r.json()["blogs"]
    for b in blogs:
        blog_id = b["id"]
        title = b["title"]
        print(f"Blog ID: {blog_id} - {title}")
else:
    print(f"Error: {r.status_code}")
