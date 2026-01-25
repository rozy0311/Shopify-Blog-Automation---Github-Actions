import os
import requests
import json

SHOP = os.environ.get("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get("SHOPIFY_TOKEN")
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "108441862462")  # Sustainable Living
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

if not TOKEN:
    raise SystemExit("Missing SHOPIFY_ACCESS_TOKEN")

headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Get ALL published articles and find ones with issues
all_articles = []
all_issues = []

# Paginate through all articles
url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles.json?limit=250&published_status=published"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    articles = response.json().get("articles", [])
    print(f"Found {len(articles)} published articles")

    for art in articles:
        art_id = art.get("id")
        title = art.get("title", "")[:50]
        has_meta = bool(art.get("summary_html"))
        has_image = bool(art.get("image"))
        body = art.get("body_html", "") or ""
        img_count = body.count("<img")
        has_broken = (
            "Cdn Shopify" in body
            or "Image Pollinations" in body
            or "rate limit" in body.lower()
        )

        issues = []
        if not has_meta:
            issues.append("NO_META")
        if not has_image:
            issues.append("NO_FEATURED")
        if img_count < 3:
            issues.append(f"LOW_IMGS:{img_count}")
        if has_broken:
            issues.append("BROKEN_TEXT")

        if issues:
            all_issues.append({"id": art_id, "title": title, "issues": issues})

    print(f"\nTotal articles with issues: {len(all_issues)}")
    print("\n--- ARTICLES NEEDING FIX ---")
    for i, item in enumerate(all_issues[:30]):
        print(f'{i+1}. ID:{item["id"]} | {item["title"]} | {item["issues"]}')

    # Save to file for processing
    with open("articles_to_fix.json", "w") as f:
        json.dump(all_issues, f, indent=2)
    print(f"\nSaved {len(all_issues)} articles to articles_to_fix.json")
else:
    print(f"Error: {response.status_code}")
    print(response.text[:500])
