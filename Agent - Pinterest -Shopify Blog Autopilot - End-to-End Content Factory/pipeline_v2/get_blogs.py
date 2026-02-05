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
headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

response = requests.get(url, headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    blogs = response.json().get("blogs", [])
    for blog in blogs:
        print(
            f"Blog ID: {blog['id']} - Title: {blog['title']} - Handle: {blog['handle']}"
        )
else:
    print(f"Error: {response.text}")
