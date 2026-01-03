#!/usr/bin/env python3
"""
Fix meta descriptions using Shopify metafields.
Shopify articles use metafields for SEO fields, not direct article fields.
"""

import requests
import json

SHOP = "the-rike-inc.myshopify.com"
TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"
API_VERSION = "2025-01"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Meta descriptions for all 10 articles (50-160 chars)
META_DESCRIPTIONS = {
    690513117502: "Learn to make all-purpose citrus vinegar cleaner at home. This natural DIY recipe cuts grease, disinfects surfaces, and saves money.",
    690513150270: "Create streak-free natural glass cleaner with simple ingredients. Our homemade recipe works better than commercial products without toxic chemicals.",
    690513183038: "Make powerful baking soda scrub for kitchen sinks naturally. This gentle abrasive removes stains and odors without scratching stainless steel.",
    690513215806: "Complete castile soap dilution guide for every cleaning task. Learn exact ratios for dishes, floors, laundry, pets, and personal care.",
    690513248574: "Boost your laundry naturally without harsh chemicals. DIY recipes with washing soda, borax alternatives, and essential oils for cleaner clothes.",
    690513281342: "DIY fabric refresher spray eliminates odors naturally. Make Febreze alternative with vodka, essential oils, and simple ingredients at home.",
    690513314110: "Make baking soda deodorizer sachets for closets and drawers. Easy DIY project keeps clothes fresh naturally for months without chemicals.",
    690513346878: "Simple natural produce wash recipe removes pesticides and wax. Vinegar and baking soda solutions proven effective for fruits and vegetables.",
    690513379646: "Discover what lemon juice actually cleans and what it damages. Science-based guide to safe lemon cleaning for your home surfaces.",
    690513412414: "Complete kombucha first batch guide with safety tips. Step-by-step brewing instructions for beginners with troubleshooting and SCOBY care.",
}


def set_metafield(
    article_id, namespace, key, value, value_type="single_line_text_field"
):
    """Set a metafield on an article using the metafields API"""
    # First check if metafield exists
    url = (
        f"https://{SHOP}/admin/api/{API_VERSION}/articles/{article_id}/metafields.json"
    )
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code != 200:
        print(f"  ❌ Failed to get metafields: {resp.status_code}")
        return False

    metafields = resp.json().get("metafields", [])
    existing = next(
        (m for m in metafields if m["namespace"] == namespace and m["key"] == key), None
    )

    if existing:
        # Update existing metafield
        update_url = (
            f"https://{SHOP}/admin/api/{API_VERSION}/metafields/{existing['id']}.json"
        )
        payload = {
            "metafield": {"id": existing["id"], "value": value, "type": value_type}
        }
        resp = requests.put(update_url, headers=HEADERS, json=payload)
    else:
        # Create new metafield
        create_url = f"https://{SHOP}/admin/api/{API_VERSION}/articles/{article_id}/metafields.json"
        payload = {
            "metafield": {
                "namespace": namespace,
                "key": key,
                "value": value,
                "type": value_type,
            }
        }
        resp = requests.post(create_url, headers=HEADERS, json=payload)

    return resp.status_code in [200, 201]


def main():
    print("=" * 60)
    print("ADDING SEO META DESCRIPTIONS VIA METAFIELDS")
    print("=" * 60)

    success_count = 0
    for article_id, meta_desc in META_DESCRIPTIONS.items():
        # Shopify uses 'global' namespace with 'description_tag' key for SEO description
        success = set_metafield(article_id, "global", "description_tag", meta_desc)

        if success:
            success_count += 1
            print(f"✅ {article_id}: {meta_desc[:50]}...")
        else:
            print(f"❌ {article_id}: Failed to set meta description")

    print(f"\n✅ Updated {success_count}/{len(META_DESCRIPTIONS)} articles")

    # Verify one article
    print("\n📋 Verifying first article metafields...")
    url = (
        f"https://{SHOP}/admin/api/{API_VERSION}/articles/690513117502/metafields.json"
    )
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        metafields = resp.json().get("metafields", [])
        for mf in metafields:
            if mf["key"] == "description_tag":
                print(f"  description_tag: {mf['value'][:60]}...")
                break
        else:
            print("  No description_tag found")


if __name__ == "__main__":
    main()
