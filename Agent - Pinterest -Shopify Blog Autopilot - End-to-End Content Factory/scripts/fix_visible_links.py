#!/usr/bin/env python3
"""
Fix visible links in already-published articles
Removes <a href="...">text</a> and keeps just the text
Also removes References sections with visible links
"""

import requests
import re
import json

# === CONFIGURATION ===
SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"

# Article IDs to fix (topics 21-32 that were published with visible links)
# From conversation history:
ARTICLE_IDS = [
    # Topics 21-24 need to be fetched
    # Topics 25-32:
    690501091646,  # Topic 25: Preserving Lemons
    690501124414,  # Topic 26: Making Fruit Leather
    690501157182,  # Topic 27: Seed Saving
    690501189950,  # Topic 28: Homemade Yogurt
    690501222718,  # Topic 29: Upcycling Glass Jars
    690502697278,  # Topic 30: Natural Air Fresheners
    690503254334,  # Topic 31: Fermenting Vegetables
    690504433982,  # Topic 32: DIY Herbal Salves
]


def get_headers():
    return {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}


def fetch_recent_articles(limit=50):
    """Fetch recent articles to find all that need fixing"""
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json?limit={limit}"
    resp = requests.get(url, headers=get_headers(), timeout=30)
    if resp.status_code == 200:
        return resp.json().get("articles", [])
    return []


def remove_visible_links(html_content):
    """Remove visible links but keep the text content"""
    if not html_content:
        return html_content

    # Pattern to match <a href="...">text</a> and replace with just text
    # This handles various attributes like target="_blank" rel="noopener"
    pattern = r'<a\s+[^>]*href=["\'][^"\']*["\'][^>]*>([^<]*)</a>'

    # Replace links with just the text content
    fixed_html = re.sub(pattern, r"\1", html_content)

    # Remove References sections (they have visible domain names)
    # Pattern to match <h3>References</h3> and the following <ol>...</ol>
    ref_pattern = r"<hr[^>]*>\s*<h3>References</h3>\s*<ol[^>]*>.*?</ol>"
    fixed_html = re.sub(ref_pattern, "", fixed_html, flags=re.DOTALL)

    # Also try without <hr>
    ref_pattern2 = r"<h3>References</h3>\s*<ol[^>]*>.*?</ol>"
    fixed_html = re.sub(ref_pattern2, "", fixed_html, flags=re.DOTALL)

    return fixed_html


def update_article(article_id, new_body_html):
    """Update article with new body HTML"""
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"

    data = {"article": {"id": article_id, "body_html": new_body_html}}

    resp = requests.put(url, headers=get_headers(), json=data, timeout=30)
    return resp.status_code == 200


def has_visible_links(html_content):
    """Check if article has visible links that need fixing"""
    if not html_content:
        return False

    # Check for href patterns
    if re.search(r"<a\s+[^>]*href=", html_content):
        return True

    # Check for References section
    if "<h3>References</h3>" in html_content:
        return True

    return False


def main():
    print("=" * 60)
    print("FIXING VISIBLE LINKS IN PUBLISHED ARTICLES")
    print("=" * 60)

    # Fetch all recent articles
    print("\nFetching recent articles...")
    articles = fetch_recent_articles(100)
    print(f"Found {len(articles)} articles")

    fixed_count = 0
    skipped_count = 0

    for article in articles:
        article_id = article["id"]
        title = article["title"]
        body_html = article.get("body_html", "")

        if has_visible_links(body_html):
            print(f"\n🔧 Fixing: {title[:50]}... (ID: {article_id})")

            # Remove visible links
            new_body = remove_visible_links(body_html)

            # Update the article
            if update_article(article_id, new_body):
                print(f"   ✅ Fixed successfully!")
                fixed_count += 1
            else:
                print(f"   ❌ Failed to update")
        else:
            skipped_count += 1

    print("\n" + "=" * 60)
    print(f"SUMMARY:")
    print(f"  ✅ Fixed: {fixed_count} articles")
    print(f"  ⏭️  Skipped (no links): {skipped_count} articles")
    print("=" * 60)


if __name__ == "__main__":
    main()
