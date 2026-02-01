#!/usr/bin/env python3
"""
Fix all article TITLES to match META-PROMPT standard:
- Keyword-first (primary keyword in first 10 chars or 1/3 of title)
- Clear payoff (time/cost/result)
- No numeric prefix
- Template: "Primary Keyword: How to X" or "Primary Keyword: Complete Guide"
"""

import requests
import json

# === CONFIGURATION ===
SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"


def get_headers():
    return {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}


def update_article_title(article_id, new_title):
    """Update article title only"""
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"

    data = {"article": {"id": article_id, "title": new_title}}

    resp = requests.put(url, headers=get_headers(), json=data, timeout=30)
    return resp.status_code == 200


def get_all_articles():
    """Get all articles from blog"""
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json?limit=250"
    resp = requests.get(url, headers=get_headers(), timeout=30)
    if resp.status_code == 200:
        return resp.json().get("articles", [])
    return []


# Title mappings: old keyword -> new SEO title (keyword-first with payoff)
TITLE_FIXES = {
    # Topic 21
    "beeswax wraps": "Beeswax Wraps: How to Make Eco-Friendly Food Wraps at Home",
    # Topic 22
    "composting": "Composting in Small Spaces: Zero-Waste Methods for Apartments",
    # Topic 23
    "herbs indoors": "Indoor Herb Garden: Grow Fresh Herbs Year-Round (No Yard Needed)",
    # Topic 24
    "fabric dyes": "Natural Fabric Dyes: Turn Kitchen Scraps into Beautiful Colors",
    # Topic 25
    "preserving lemons": "Preserved Lemons: How to Make This Essential Pantry Staple",
    # Topic 26
    "fruit leather": "Homemade Fruit Leather: A Healthy Snack with Zero Added Sugar",
    # Topic 27
    "seed saving": "Seed Saving: How to Collect and Store Seeds for Next Season",
    # Topic 28
    "homemade yogurt": "Homemade Yogurt: No Special Equipment Required (Easy Method)",
    # Topic 29
    "glass jars": "Upcycled Glass Jars: Creative Storage Solutions for Every Room",
    # Topic 30
    "air fresheners": "Natural Air Fresheners: DIY Recipes That Actually Work",
    # Topic 31
    "fermenting vegetables": "Fermenting Vegetables: A Beginner's Guide to Probiotic-Rich Foods",
    # Topic 32
    "herbal salves": "Herbal Salves and Balms: Make Your Own Natural Remedies",
    # Topic 33
    "microgreens": "Growing Microgreens Indoors: Fresh Greens in Just One Week",
}


def main():
    print("Fetching all articles...")
    articles = get_all_articles()
    print(f"Found {len(articles)} articles")

    updated = 0
    skipped = 0

    for keyword, new_title in TITLE_FIXES.items():
        # Find article matching keyword
        for article in articles:
            old_title = article["title"].lower()
            if keyword.lower() in old_title:
                article_id = article["id"]
                current_title = article["title"]

                # Check if already fixed
                if current_title == new_title:
                    print(f"⏭️  Already fixed: {new_title}")
                    skipped += 1
                    continue

                print(f"\n📝 Updating: {current_title}")
                print(f"   → New: {new_title}")

                if update_article_title(article_id, new_title):
                    print(f"   ✅ SUCCESS!")
                    updated += 1
                else:
                    print(f"   ❌ FAILED!")
                break

    print(f"\n{'='*50}")
    print(f"✅ Updated: {updated}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"📊 Total processed: {updated + skipped}")


if __name__ == "__main__":
    main()
