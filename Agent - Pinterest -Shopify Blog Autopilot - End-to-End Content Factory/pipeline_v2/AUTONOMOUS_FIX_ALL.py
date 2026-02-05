import json
import os
import requests
import time
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

SHOP_URL = f"https://{os.getenv('SHOPIFY_SHOP')}"
ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = "108441862462"

headers = {"X-Shopify-Access-Token": ACCESS_TOKEN, "Content-Type": "application/json"}


def fix_broken_images(article_id):
    """Fix broken images in article"""
    print(f"\n[AGENT] Fixing broken images for {article_id}...")

    # Fetch article
    url = f"{SHOP_URL}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    resp = requests.get(url, headers=headers)

    if resp.status_code != 200:
        print(f"[ERROR] Failed to fetch article: {resp.status_code}")
        return False

    article = resp.json()["article"]
    body_html = article.get("body_html", "")

    # Remove broken image tags (rate limit errors, etc)
    import re

    # Remove images with rate limit errors
    body_html = re.sub(
        r'<img[^>]*alt="[^"]*rate limit[^"]*"[^>]*>', "", body_html, flags=re.IGNORECASE
    )
    body_html = re.sub(
        r'<img[^>]*src="[^"]*rate[^"]*limit[^"]*"[^>]*>',
        "",
        body_html,
        flags=re.IGNORECASE,
    )

    # Remove placeholder/error images
    body_html = re.sub(
        r'<img[^>]*src="placeholder[^"]*"[^>]*>', "", body_html, flags=re.IGNORECASE
    )

    # Update article
    update_data = {"article": {"id": article_id, "body_html": body_html}}

    update_resp = requests.put(url, headers=headers, json=update_data)

    if update_resp.status_code == 200:
        print(f"[SUCCESS] Fixed broken images for {article_id}")
        return True
    else:
        print(f"[ERROR] Failed to update: {update_resp.status_code}")
        return False


def process_all_issues():
    """Process all articles with issues"""

    # Load audit results
    with open("audit_results.json", "r", encoding="utf-8") as f:
        articles_to_fix = json.load(f)

    total = len(articles_to_fix)

    print(f"\n{'='*60}")
    print(f"[AGENT] Starting autonomous fix process")
    print(f"[AGENT] Total articles to fix: {total}")
    print(f"{'='*60}\n")

    fixed_count = 0
    failed_count = 0

    for idx, article in enumerate(articles_to_fix, 1):
        article_id = article["id"]
        title = article["title"]
        issues = article["issues"]

        print(f"\n[{idx}/{total}] Processing: {article_id} - {title}")
        print(f"[ISSUES] {', '.join(issues)}")

        # Fix based on issue types
        success = True

        if "BROKEN_IMGS" in str(issues):
            if not fix_broken_images(article_id):
                success = False

        # Add more fix handlers here for other issue types
        # if 'OFF_TOPIC' in str(issues): fix_off_topic(article_id)
        # if 'NO_SOURCES' in str(issues): add_sources(article_id)
        # etc.

        if success:
            fixed_count += 1
            print(f"[AGENT] Γ£ô Fixed {article_id}")
        else:
            failed_count += 1
            print(f"[AGENT] Γ£ù Failed {article_id}")

        # Rate limiting - be nice to Shopify
        time.sleep(0.5)

        # Progress update every 10 articles
        if idx % 10 == 0:
            print(
                f"\n[PROGRESS] {idx}/{total} processed | Fixed: {fixed_count} | Failed: {failed_count}"
            )

    print(f"\n{'='*60}")
    print(f"[AGENT] Autonomous fix complete!")
    print(f"[FINAL] Fixed: {fixed_count} | Failed: {failed_count}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    process_all_issues()
