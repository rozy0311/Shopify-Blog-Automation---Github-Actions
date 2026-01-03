"""
Check and cleanup duplicate articles on Shopify blog
"""

import requests
from collections import defaultdict

SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"

HEADERS = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}


def get_all_articles():
    """Get all articles from the blog"""
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json?limit=250"
    response = requests.get(url, headers=HEADERS)
    return response.json().get("articles", [])


def delete_article(article_id):
    """Delete an article"""
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    response = requests.delete(url, headers=HEADERS)
    return response.status_code == 200


def find_and_remove_duplicates():
    """Find duplicate articles by title and remove older ones"""
    articles = get_all_articles()
    print(f"Total articles: {len(articles)}")

    # Group by title
    by_title = defaultdict(list)
    for article in articles:
        title = article["title"]
        by_title[title].append(article)

    # Find duplicates
    duplicates_found = 0
    deleted_count = 0

    for title, articles_list in by_title.items():
        if len(articles_list) > 1:
            duplicates_found += 1
            print(f"\n🔄 DUPLICATE: {title}")

            # Sort by ID (higher = newer)
            articles_list.sort(key=lambda x: x["id"], reverse=True)

            # Keep the newest (first), delete the rest
            keep = articles_list[0]
            print(f"   ✓ KEEP: ID {keep['id']}")

            for dup in articles_list[1:]:
                print(f"   ✗ DELETE: ID {dup['id']}")
                if delete_article(dup["id"]):
                    deleted_count += 1
                    print(f"     ✅ Deleted")
                else:
                    print(f"     ❌ Failed to delete")

    print(f"\n" + "=" * 50)
    print(f"Duplicate titles found: {duplicates_found}")
    print(f"Articles deleted: {deleted_count}")
    print(f"=" * 50)


if __name__ == "__main__":
    find_and_remove_duplicates()
