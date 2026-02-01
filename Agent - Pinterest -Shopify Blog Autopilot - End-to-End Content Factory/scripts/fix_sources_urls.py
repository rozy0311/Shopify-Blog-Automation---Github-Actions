"""
Fix Sources in already published articles
Converts raw URLs to proper anchor links
"""

import requests
import re

SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
API_VERSION = "2025-01"
BLOG_ID = "108441862462"

headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}

# Articles that need fixing (published by batch script with raw URLs)
# Add article IDs here as they're published
ARTICLES_TO_FIX = [
    690496045374,  # Topic 19: DIY Citrus Cleaner
    # Add more IDs as needed
]


def fix_sources_in_article(article_id):
    """Fix Sources section to use proper anchor links"""

    # Get current article
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/articles/{article_id}.json"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Failed to get article {article_id}: {response.status_code}")
        return False

    article = response.json()["article"]
    body_html = article["body_html"]
    title = article["title"]

    print(f"\n📝 Fixing: {title} (ID: {article_id})")

    # Pattern to find raw URL sources like:
    # <li>Source Name - https://example.com</li>
    # or <li>Source Name: https://example.com</li>
    pattern = r"<li>([^<]+?)\s*[-:]\s*(https?://[^\s<]+)</li>"

    def replace_with_anchor(match):
        source_name = match.group(1).strip()
        url = match.group(2).strip()
        return (
            f'<li><a href="{url}" target="_blank" rel="noopener">{source_name}</a></li>'
        )

    # Replace all raw URL sources
    new_body_html = re.sub(pattern, replace_with_anchor, body_html)

    # Check if changes were made
    if new_body_html == body_html:
        print(f"  ⚠️ No changes needed or pattern not found")
        return True

    # Update article
    update_data = {"article": {"id": article_id, "body_html": new_body_html}}

    update_url = (
        f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/articles/{article_id}.json"
    )
    update_response = requests.put(update_url, headers=headers, json=update_data)

    if update_response.status_code == 200:
        print(f"  ✅ Sources fixed successfully!")
        return True
    else:
        print(f"  ❌ Failed to update: {update_response.status_code}")
        return False


def get_recent_articles(limit=20):
    """Get recent articles to check for Source issues"""
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles.json?limit={limit}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"❌ Failed to get articles: {response.status_code}")
        return []

    return response.json().get("articles", [])


def find_articles_with_raw_urls():
    """Find all articles that have raw URLs in Sources section"""
    articles = get_recent_articles(100)
    articles_to_fix = []

    print(f"\n🔍 Scanning {len(articles)} articles for raw URL sources...")

    pattern = r"<li>[^<]+[-:]\s*https?://[^\s<]+</li>"

    for article in articles:
        if re.search(pattern, article.get("body_html", "")):
            articles_to_fix.append({"id": article["id"], "title": article["title"]})
            print(f"  ⚠️ Found raw URLs in: {article['title']}")

    return articles_to_fix


def main():
    print("\n" + "=" * 60)
    print("🔧 FIX SOURCES - Convert Raw URLs to Anchor Links")
    print("=" * 60)

    # Find articles that need fixing
    articles_to_fix = find_articles_with_raw_urls()

    if not articles_to_fix:
        print("\n✅ No articles need fixing!")
        return

    print(f"\n📋 Found {len(articles_to_fix)} articles to fix")

    # Fix each article
    success = 0
    failed = 0

    for article in articles_to_fix:
        if fix_sources_in_article(article["id"]):
            success += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print("📊 COMPLETE!")
    print("=" * 60)
    print(f"✅ Fixed: {success}")
    print(f"❌ Failed: {failed}")


if __name__ == "__main__":
    main()
