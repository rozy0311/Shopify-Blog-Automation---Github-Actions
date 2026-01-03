"""Check article status"""

import requests

SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"
headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}

url = (
    f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json?limit=250"
)
response = requests.get(url, headers=headers)
articles = response.json().get("articles", [])

print("=" * 60)
print(f"TOTAL ARTICLES: {len(articles)}")
print("=" * 60)

print("\n=== MOST RECENT 30 ARTICLES ===")
for i, a in enumerate(articles[:30], 1):
    title = a["title"][:55]
    print(f"{i:2}. {title}")

print("\n=== CHECKING FOR BATCH ARTICLES ===")
batch_count = 0
for a in articles:
    body = a.get("body_html", "")
    if "Welcome to our comprehensive guide" in body:
        batch_count += 1

print(f"Articles with generic opening (need fixing): {batch_count}")
