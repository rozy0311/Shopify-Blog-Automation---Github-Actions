#!/usr/bin/env python3
"""Batch fix articles with generic content."""

import os
import sys
import requests
import time
from dotenv import load_dotenv

load_dotenv()

# Import the fix function
sys.path.insert(0, ".")
from ai_orchestrator import strip_generic_sections

store = os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
if not store.startswith("http"):
    store = "https://" + store
token = os.getenv("SHOPIFY_ACCESS_TOKEN")
blog_id = os.getenv("SHOPIFY_BLOG_ID")

article_ids = [
    691791888702,
    691731595582,
    691731562814,
    691731530046,
    690770870590,
    690770805054,
    690770772286,
    690770739518,
]

print(f"Fixing {len(article_ids)} articles...")
print()

fixed_count = 0
for aid in article_ids:
    # Fetch article
    url = f"{store}/admin/api/2025-01/blogs/{blog_id}/articles/{aid}.json"
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    r = requests.get(url, headers=headers)
    article = r.json().get("article", {})
    title = article.get("title", "Unknown")[:40]
    body = article.get("body_html", "")

    # Apply fix
    cleaned = strip_generic_sections(body, title)
    removed = len(body) - len(cleaned)

    if removed > 0:
        # Update article
        data = {"article": {"id": aid, "body_html": cleaned}}
        r2 = requests.put(url, headers=headers, json=data)
        success = r2.status_code == 200
        status = "OK" if success else "FAILED"
        print(f"[FIXED] {aid}: {title} (removed {removed} chars) - {status}")
        if success:
            fixed_count += 1
    else:
        print(f"[SKIP]  {aid}: {title} (no changes needed)")

    time.sleep(0.5)  # Rate limit

print()
print(f"Done! Fixed {fixed_count}/{len(article_ids)} articles.")
