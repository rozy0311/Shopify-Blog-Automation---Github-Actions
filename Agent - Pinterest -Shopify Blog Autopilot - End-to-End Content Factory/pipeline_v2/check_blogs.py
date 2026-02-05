import os
import requests
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

SHOP = os.getenv("SHOPIFY_SHOP")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

# Get all blogs first
url = f"https://{SHOP}/admin/api/2025-01/blogs.json"
headers = {"X-Shopify-Access-Token": TOKEN}
resp = requests.get(url, headers=headers)
print("Blogs:", resp.json())
