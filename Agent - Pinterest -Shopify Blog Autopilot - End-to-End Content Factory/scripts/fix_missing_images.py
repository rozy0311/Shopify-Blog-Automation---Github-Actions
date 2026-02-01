#!/usr/bin/env python3
"""
Fix missing images for republished articles (Topics 21-33)
Uses Pexels API to find appropriate images
"""

import requests
import time

SHOP = "the-rike-inc.myshopify.com"
TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"
PEXELS_API_KEY = "os.environ.get("PEXELS_API_KEY", "")"

# Topic -> Pexels search query mapping
TOPIC_IMAGES = {
    "Beeswax Wraps": "beeswax wrap eco friendly",
    "Composting": "compost food scraps kitchen",
    "Indoor Herb": "herbs indoor kitchen garden",
    "Natural Fabric Dye": "natural dye fabric textile",
    "Preserved Lemon": "preserved lemons jar moroccan",
    "Fruit Leather": "fruit snacks dried healthy",
    "Seed Saving": "seeds saving garden harvest",
    "Homemade Yogurt": "homemade yogurt fermented milk",
    "Upcycled Glass Jar": "glass jars upcycle storage",
    "Natural Air Freshener": "natural air freshener essential oils",
    "Fermenting Vegetable": "fermented vegetables kimchi sauerkraut",
    "Herbal Salve": "herbal salve balm natural remedies",
    "Microgreens": "microgreens growing indoor fresh",
}


def get_pexels_image(query):
    """Get image from Pexels API"""
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": 1, "orientation": "landscape"}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get("photos"):
            photo = data["photos"][0]
            return {
                "src": photo["src"]["large2x"],  # High quality
                "alt": f"{query} - Photo from Pexels",
            }
    return None


def get_all_articles():
    """Get all articles from the blog"""
    url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json"
    headers = {"X-Shopify-Access-Token": TOKEN}
    params = {"limit": 250}

    response = requests.get(url, headers=headers, params=params)
    return response.json().get("articles", [])


def update_article_image(article_id, image_src, image_alt):
    """Update article with new image"""
    url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

    payload = {
        "article": {"id": article_id, "image": {"src": image_src, "alt": image_alt}}
    }

    response = requests.put(url, headers=headers, json=payload)
    return response


def main():
    print("🖼️  Fixing Missing Images for Topics 21-33")
    print("=" * 60)

    articles = get_all_articles()
    print(f"Found {len(articles)} articles\n")

    fixed = 0
    skipped = 0

    for article in articles:
        title = article["title"]
        article_id = article["id"]
        has_image = article.get("image") is not None

        # Check if this article matches our topics
        matched_topic = None
        for topic_key in TOPIC_IMAGES:
            if topic_key.lower() in title.lower():
                matched_topic = topic_key
                break

        if matched_topic:
            if has_image:
                print(f"✅ {title[:50]}... already has image")
                skipped += 1
            else:
                print(f"📷 {title[:50]}...")
                print(f"   → Missing image, fetching from Pexels...")

                # Get image from Pexels
                query = TOPIC_IMAGES[matched_topic]
                image_data = get_pexels_image(query)

                if image_data:
                    response = update_article_image(
                        article_id, image_data["src"], image_data["alt"]
                    )
                    if response.status_code == 200:
                        print(f"   → ✅ Image added successfully!")
                        fixed += 1
                    else:
                        print(f"   → ❌ Error: {response.status_code}")
                else:
                    print(f"   → ❌ No image found on Pexels")

                # Rate limiting
                time.sleep(0.5)

    print("\n" + "=" * 60)
    print(f"✅ Fixed: {fixed}")
    print(f"⏭️  Already had images: {skipped}")


if __name__ == "__main__":
    main()
