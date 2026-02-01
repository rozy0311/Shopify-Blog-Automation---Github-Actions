#!/usr/bin/env python3
"""
Fix featured images for all 10 articles with topic-specific images
"""

import requests
import time

SHOP = "the-rike-inc.myshopify.com"
TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"
API_VERSION = "2025-01"

HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Topic-specific featured images from Pexels (high quality, relevant)
FEATURED_IMAGES = {
    690513117502: {
        "title": "Citrus Vinegar Cleaner",
        "image_url": "https://images.pexels.com/photos/1414110/pexels-photo-1414110.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "alt": "Fresh citrus fruits including oranges and lemons for natural DIY cleaning solution",
    },
    690513150270: {
        "title": "Glass Cleaner",
        "image_url": "https://images.pexels.com/photos/6444266/pexels-photo-6444266.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "alt": "Crystal clear window sparkling after natural cleaning with streak-free finish",
    },
    690513183038: {
        "title": "Baking Soda Scrub",
        "image_url": "https://images.pexels.com/photos/6197126/pexels-photo-6197126.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "alt": "Clean stainless steel kitchen sink with natural baking soda cleaning supplies",
    },
    690513215806: {
        "title": "Castile Soap Dilution",
        "image_url": "https://images.pexels.com/photos/4239014/pexels-photo-4239014.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "alt": "Pure liquid castile soap in glass bottle for natural household cleaning",
    },
    690513248574: {
        "title": "Laundry Booster",
        "image_url": "https://images.pexels.com/photos/5591464/pexels-photo-5591464.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "alt": "Fresh clean laundry with natural washing ingredients and eco-friendly detergent",
    },
    690513281342: {
        "title": "Fabric Refresher",
        "image_url": "https://images.pexels.com/photos/4239082/pexels-photo-4239082.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "alt": "Natural fabric refresher spray bottle with lavender essential oil and fresh linens",
    },
    690513314110: {
        "title": "Deodorizer Sachets",
        "image_url": "https://images.pexels.com/photos/6621472/pexels-photo-6621472.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "alt": "Handmade lavender sachets with dried flowers for natural closet deodorizing",
    },
    690513346878: {
        "title": "Produce Wash",
        "image_url": "https://images.pexels.com/photos/1128678/pexels-photo-1128678.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "alt": "Fresh organic vegetables and fruits being washed with natural produce cleaner",
    },
    690513379646: {
        "title": "Lemon Juice Cleaning",
        "image_url": "https://images.pexels.com/photos/1414122/pexels-photo-1414122.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "alt": "Fresh lemons sliced for natural cleaning with citric acid cleaning power",
    },
    690513412414: {
        "title": "Kombucha First Batch",
        "image_url": "https://images.pexels.com/photos/8329281/pexels-photo-8329281.jpeg?auto=compress&cs=tinysrgb&w=1200",
        "alt": "Homemade kombucha brewing in glass jar with SCOBY for fermented tea drink",
    },
}


def set_featured_image(article_id, image_url, alt_text):
    """Set featured image for article using image URL"""
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"

    payload = {
        "article": {"id": article_id, "image": {"src": image_url, "alt": alt_text}}
    }

    resp = requests.put(url, headers=HEADERS, json=payload)
    return resp.status_code == 200, resp.text[:200] if resp.status_code != 200 else "OK"


def main():
    print("=" * 70)
    print("ADDING FEATURED IMAGES TO ALL 10 ARTICLES")
    print("=" * 70)

    success_count = 0

    for article_id, data in FEATURED_IMAGES.items():
        print(f"\n[{article_id}] {data['title']}")
        print(f"   Image: {data['image_url'][:60]}...")

        ok, msg = set_featured_image(article_id, data["image_url"], data["alt"])

        if ok:
            print(f"   ✅ Featured image added successfully")
            success_count += 1
        else:
            print(f"   ❌ Failed: {msg}")

        time.sleep(0.5)  # Rate limiting

    print(f"\n{'=' * 70}")
    print(f"RESULT: {success_count}/10 articles updated with featured images")
    print("=" * 70)


if __name__ == "__main__":
    main()
