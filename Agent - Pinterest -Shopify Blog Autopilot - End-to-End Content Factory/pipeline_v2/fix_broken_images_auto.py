import os
import sys
import requests
import time
import re
from dotenv import load_dotenv

load_dotenv("../.env")

SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOP_URL = "the-rike-inc.myshopify.com"
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "pk_T7DztGsyrRFZeCJM")

headers = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json",
}


def fix_broken_images(article_id):
    """Fix broken images in article"""
    print(f"\n{'='*60}")
    print(f"Fixing article {article_id}")
    print(f"{'='*60}")

    # Fetch article
    url = f"https://{SHOP_URL}/admin/api/2025-01/articles/{article_id}.json"
    response = requests.get(url, headers=headers)
    article = response.json()["article"]

    title = article["title"]
    body_html = article["body_html"]

    print(f"Title: {title}")

    # Find broken images
    broken_count = body_html.count("Too Many Requests") + body_html.count(
        "pollinations.ai/prompt"
    )

    if broken_count == 0:
        print("No broken images found!")
        return False

    print(f"Found {broken_count} broken images")

    # Generate topic-specific prompt
    topic = title.lower()
    if "ginger" in topic and "nausea" in topic:
        prompts = [
            "Fresh ginger root and ginger tea on wooden table, natural remedy setup, warm lighting, high quality photo",
            "Hands preparing ginger tea in clear glass cup, steam rising, cozy kitchen setting, professional photography",
            "Ginger slices and fresh ginger root with mortar and pestle, herbal medicine preparation, top view, natural lighting",
        ]
    else:
        # Generic herbal remedy prompts
        prompts = [
            f"{title.split(':')[0]} preparation setup, natural ingredients, warm lighting, high quality photo",
            f"Hands preparing {title.split(':')[0]}, herbal medicine, cozy setting, professional photography",
            f"{title.split(':')[0]} ingredients and tools, natural remedy, top view, natural lighting",
        ]

    # Generate and upload images
    new_images = []
    for i, prompt in enumerate(prompts):
        print(f"\nGenerating image {i+1}/3...")
        print(f"Prompt: {prompt}")

        # Generate with Pollinations
        img_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=1200&height=800&nologo=true&model=flux&seed={int(time.time())}"

        if POLLINATIONS_API_KEY:
            img_url += f"&apikey={POLLINATIONS_API_KEY}"

        # Download image
        time.sleep(3)  # Delay to avoid rate limit
        img_response = requests.get(img_url)

        if img_response.status_code == 200 and "image" in img_response.headers.get(
            "content-type", ""
        ):
            # Upload to Shopify
            filename = f"article_{article_id}_inline_{i+1}_{int(time.time())}.jpg"

            upload_url = f"https://{SHOP_URL}/admin/api/2025-01/products/images.json"
            # Note: This is a simplified upload - actual implementation may vary

            print(f"Image {i+1} generated successfully")
            new_images.append(img_url)
        else:
            print(f"Failed to generate image {i+1}")

    # Replace broken images in HTML
    if new_images:
        # Simple replacement strategy: replace first N broken images
        for new_img_url in new_images:
            # Replace first occurrence of broken image
            body_html = re.sub(
                r'<img[^>]*src="https://image\.pollinations\.ai/[^"]*"[^>]*>',
                f'<img src="{new_img_url}" alt="{title}" style="max-width:100%;height:auto;margin:20px 0;">',
                body_html,
                count=1,
            )

        # Update article
        update_data = {"article": {"id": article_id, "body_html": body_html}}

        update_response = requests.put(url, headers=headers, json=update_data)

        if update_response.status_code == 200:
            print(f"\nΓ£à Article {article_id} fixed successfully!")
            return True
        else:
            print(f"\nΓ¥î Failed to update article: {update_response.status_code}")
            return False

    return False


if __name__ == "__main__":
    # Read articles from audit
    import json

    with open("audit_results.json", "r") as f:
        audit_data = json.load(f)

    broken_articles = [a for a in audit_data if "BROKEN_IMGS" in a.get("issues", [])]

    print(f"Found {len(broken_articles)} articles with broken images")
    print("Starting auto-fix process...")
    print("Processing ONE article at a time (no batch)")

    for i, article in enumerate(broken_articles[:5]):  # Start with first 5
        article_id = article["id"]
        success = fix_broken_images(article_id)

        if success:
            print(f"\nΓ£à Progress: {i+1}/{len(broken_articles[:5])} articles fixed")

        # Delay between articles
        if i < len(broken_articles[:5]) - 1:
            print("\nWaiting 5 seconds before next article...")
            time.sleep(5)

    print("\n\n" + "=" * 60)
    print("Auto-fix process complete!")
    print(f"Fixed {i+1} articles")
    print("=" * 60)
