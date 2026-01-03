#!/usr/bin/env python3
"""
Fix 3 failed articles:
- 690513183038 (Baking Soda Scrub): Add 1 inline image
- 690513215806 (Castile Soap): Add 2 inline images
- 690513281342 (Fabric Refresher): Add 1 inline image + 1 figure

Also add meta_description to all 10 articles.
"""

import requests
import re

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

# Additional images needed for failed articles
FIXES = {
    690513183038: {  # Baking Soda Scrub - needs 1 more inline image
        "images_to_add": [
            {
                "src": "https://images.unsplash.com/photo-1584568694244-14fbdf83bd30?w=800",
                "alt": "Scrubbing kitchen sink with baking soda paste using sponge",
                "caption": "Apply gentle circular motions when scrubbing with baking soda paste",
            }
        ],
        "insert_after": "Additional Tips for Best Results",
    },
    690513215806: {  # Castile Soap - needs 2 more inline images
        "images_to_add": [
            {
                "src": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800",
                "alt": "Diluting castile soap in glass spray bottle with measuring cup",
                "caption": "Use distilled water for longer shelf life when diluting castile soap",
            },
            {
                "src": "https://images.unsplash.com/photo-1563453392212-326f5e854473?w=800",
                "alt": "Multiple castile soap cleaning products lined up for different uses",
                "caption": "One bottle of castile soap can replace dozens of cleaning products",
            },
        ],
        "insert_after": "Dilution Ratios by Use",
    },
    690513281342: {  # Fabric Refresher - needs 1 more image + figure
        "images_to_add": [
            {
                "src": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800",
                "alt": "Spraying fabric refresher on sofa cushions and upholstery",
                "caption": "Spray fabric refresher from 6-8 inches away for even coverage",
            }
        ],
        "insert_after": "How to Use Your Fabric Refresher",
    },
}


def get_article(article_id):
    """Fetch article from Shopify"""
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()["article"]
    return None


def update_article(article_id, updates):
    """Update article in Shopify"""
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    resp = requests.put(url, headers=HEADERS, json={"article": updates})
    return resp.status_code == 200


def add_images_to_body(body, images, insert_after):
    """Insert figure tags with images after specified heading"""
    image_html = ""
    for img in images:
        image_html += f"""
<figure>
    <img src="{img['src']}" alt="{img['alt']}" loading="lazy" style="width:100%;max-width:800px;border-radius:12px;">
    <figcaption>{img['caption']}</figcaption>
</figure>
"""

    # Find the heading and insert after the next paragraph
    pattern = rf"(<h[23][^>]*>[^<]*{re.escape(insert_after)}[^<]*</h[23]>)"
    match = re.search(pattern, body, re.IGNORECASE)

    if match:
        # Insert after the heading
        insert_pos = match.end()
        # Find the end of the next paragraph
        next_p = body.find("</p>", insert_pos)
        if next_p != -1:
            insert_pos = next_p + 4
        body = body[:insert_pos] + image_html + body[insert_pos:]
    else:
        # Fallback: insert before last </div> or at end
        last_div = body.rfind("</div>")
        if last_div != -1:
            body = body[:last_div] + image_html + body[last_div:]
        else:
            body += image_html

    return body


def main():
    print("=" * 60)
    print("FIXING FAILED ARTICLES + ADDING META DESCRIPTIONS")
    print("=" * 60)

    # First, add meta descriptions to ALL articles
    print("\n📝 Adding meta_description to all 10 articles...")
    for article_id, meta_desc in META_DESCRIPTIONS.items():
        success = update_article(article_id, {"meta_description": meta_desc})
        status = "✅" if success else "❌"
        print(f"  {status} {article_id}: {meta_desc[:50]}...")

    # Then fix the 3 failed articles
    print("\n🔧 Fixing inline images for 3 failed articles...")
    for article_id, fix_data in FIXES.items():
        article = get_article(article_id)
        if not article:
            print(f"  ❌ Failed to fetch {article_id}")
            continue

        title = article["title"][:40]
        body = article["body_html"]

        # Add missing images
        new_body = add_images_to_body(
            body, fix_data["images_to_add"], fix_data["insert_after"]
        )

        # Update article
        success = update_article(article_id, {"body_html": new_body})
        status = "✅" if success else "❌"
        images_added = len(fix_data["images_to_add"])
        print(f"  {status} {article_id}: Added {images_added} image(s) to '{title}'")

    print("\n✅ All fixes applied!")
    print("Run pre_publish_review.py to verify.")


if __name__ == "__main__":
    main()
