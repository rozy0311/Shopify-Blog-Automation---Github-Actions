#!/usr/bin/env python3
"""Post-image cleanup: remove title spam and generic phrases reintroduced by fix_images_properly.py.

Usage:
    python post_image_cleanup.py <article_id>

This script runs AFTER fix_images_properly.py and BEFORE pre_publish_review.py
to clean up title occurrences that get reintroduced via alt= and <figcaption> tags.
"""

import os
import sys
import requests


def main():
    if len(sys.argv) < 2:
        print("Usage: python post_image_cleanup.py <article_id>")
        sys.exit(1)

    article_id = sys.argv[1]

    # Import cleanup functions from ai_orchestrator
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from ai_orchestrator import _remove_title_spam, _remove_generic_phrases

    shop = os.environ.get("SHOPIFY_SHOP", "")
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
    api_version = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

    if not shop or not token:
        print("[WARN] Post-image cleanup: missing SHOPIFY_SHOP or SHOPIFY_ACCESS_TOKEN")
        sys.exit(0)  # Non-critical, don't fail the pipeline

    url = f"https://{shop}/admin/api/{api_version}/articles/{article_id}.json"
    headers = {"X-Shopify-Access-Token": token}

    # Fetch current article
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        print(f"[WARN] Post-image cleanup: fetch failed ({resp.status_code})")
        sys.exit(0)

    article = resp.json().get("article", {})
    body = article.get("body_html", "")
    title = article.get("title", "")

    if not body or not title:
        print("Post-image cleanup: no body or title, skipping")
        sys.exit(0)

    # Apply cleanup
    cleaned = _remove_title_spam(body, title)
    cleaned = _remove_generic_phrases(cleaned)

    if cleaned == body:
        print("Post-image cleanup: no changes needed")
        sys.exit(0)

    # Count what was cleaned
    old_title_count = body.lower().count(title.lower())
    new_title_count = cleaned.lower().count(title.lower())
    print(f"Post-image cleanup: title count {old_title_count} -> {new_title_count}")

    # Update article
    payload = {"article": {"id": int(article_id), "body_html": cleaned}}
    put_headers = {**headers, "Content-Type": "application/json"}
    put_resp = requests.put(url, json=payload, headers=put_headers, timeout=30)

    if put_resp.status_code == 200:
        print(f"Post-image cleanup: OK (article {article_id} updated)")
    else:
        print(f"[WARN] Post-image cleanup: update failed ({put_resp.status_code})")


if __name__ == "__main__":
    main()
