#!/usr/bin/env python3
"""
Delete ONLY the batch-generated articles (Topics 19-70) created today.
Does NOT touch older quality articles.
"""

import requests
from datetime import datetime, timezone

# Shopify API config
SHOP = "the-rike-inc.myshopify.com"
TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"
API_VERSION = "2025-01"

HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Exact titles of batch articles (Topics 19-70) - these are the ones to delete
BATCH_TITLES = [
    "DIY Citrus Cleaner from Orange Peels",
    "Homemade Soap from Kitchen Ingredients",
    "Natural Fabric Softener with Vinegar",
    "Upcycled Glass Jar Organizers",
    "Beeswax Food Wraps at Home",
    "DIY Compost Bin from Pallets",
    "Homemade Laundry Detergent Pods",
    "Repurposed T-Shirt Tote Bags",
    "Natural Room Spray with Essential Oils",
    "DIY Seed Starter Pots from Newspaper",
    "Homemade Lip Balm with Beeswax",
    "Upcycled Tin Can Planters",
    "Natural Dish Soap from Castile",
    "DIY Dryer Balls from Wool",
    "Repurposed Wine Cork Board",
    "Homemade Body Butter with Shea",
    "Natural Carpet Freshener DIY",
    "Upcycled Denim Coasters",
    "DIY Soy Candles at Home",
    "Homemade Deodorant with Coconut Oil",
    "Natural Wood Polish with Olive Oil",
    "Repurposed Mason Jar Soap Dispenser",
    "DIY Herbal Sachets for Drawers",
    "Homemade Face Mask with Honey",
    "Natural Ant Repellent DIY",
    "Upcycled Sweater Pillow Covers",
    "DIY Bath Bombs at Home",
    "Homemade Hand Sanitizer Gel",
    "Natural Jewelry Cleaner DIY",
    "Repurposed Ladder Shelf",
    "DIY Herb Drying Rack",
    "Homemade Sugar Scrub Recipes",
    "Natural Stain Remover DIY",
    "Upcycled Book Page Art",
    "DIY Floating Shelves from Reclaimed Wood",
    "Homemade Toothpaste with Baking Soda",
    "Natural Mothball Alternatives DIY",
    "Repurposed Tire Ottoman",
    "DIY Macrame Plant Hangers",
    "Homemade Hair Mask with Avocado",
    "Natural Weed Killer DIY",
    "Upcycled Pallet Coffee Table",
    "DIY Reusable Produce Bags",
    "Homemade Shaving Cream Natural",
    "Natural Rust Remover DIY",
    "Repurposed Suitcase Pet Bed",
    "DIY Essential Oil Diffuser",
    "Homemade Muscle Rub with Peppermint",
    "Natural Grout Cleaner DIY",
    "Upcycled Bottle Cap Magnets",
    "DIY Rainwater Collection System",
    "Homemade Cuticle Oil Recipe",
]


def get_all_articles():
    """Fetch all articles from the blog"""
    articles = []
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles.json"
    params = {"limit": 250}

    while url:
        response = requests.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        data = response.json()
        articles.extend(data.get("articles", []))

        # Check for pagination
        link_header = response.headers.get("Link", "")
        if 'rel="next"' in link_header:
            for link in link_header.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<> ")
                    params = {}
                    break
        else:
            url = None

    return articles


def delete_article(article_id):
    """Delete an article by ID"""
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    response = requests.delete(url, headers=HEADERS)
    return response.status_code == 200


def main():
    print("Fetching all articles...")
    articles = get_all_articles()
    print(f"Total articles in blog: {len(articles)}")

    # Find batch articles by exact title match
    batch_articles = []
    other_articles = []

    for article in articles:
        title = article.get("title", "")
        if title in BATCH_TITLES:
            batch_articles.append(article)
        else:
            other_articles.append(article)

    print(f"\n=== BATCH ARTICLES TO DELETE ({len(batch_articles)}) ===")
    for a in batch_articles:
        created = a.get("created_at", "")[:10]
        print(f"  - [{created}] {a['title']}")

    print(f"\n=== OTHER ARTICLES (KEEPING) ({len(other_articles)}) ===")
    for a in other_articles:
        created = a.get("created_at", "")[:10]
        print(f"  - [{created}] {a['title']}")

    if not batch_articles:
        print("\nNo batch articles found to delete!")
        return

    # Confirm deletion
    print(f"\n⚠️  Will delete {len(batch_articles)} batch articles.")
    print("Type 'DELETE' to confirm, or anything else to cancel:")
    confirm = input().strip()

    if confirm != "DELETE":
        print("Cancelled.")
        return

    # Delete batch articles
    deleted = 0
    failed = 0

    for article in batch_articles:
        article_id = article["id"]
        title = article["title"]

        if delete_article(article_id):
            print(f"✅ Deleted: {title}")
            deleted += 1
        else:
            print(f"❌ Failed: {title}")
            failed += 1

    print(f"\n=== SUMMARY ===")
    print(f"Deleted: {deleted}")
    print(f"Failed: {failed}")
    print(f"Kept: {len(other_articles)} articles")


if __name__ == "__main__":
    main()
