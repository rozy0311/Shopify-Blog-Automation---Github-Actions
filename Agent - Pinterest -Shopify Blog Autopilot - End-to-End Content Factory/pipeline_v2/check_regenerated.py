#!/usr/bin/env python3
"""Check regenerated articles for missing elements."""
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

store = "https://" + os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
token = os.getenv("SHOPIFY_ACCESS_TOKEN")
blog_id = os.getenv("SHOPIFY_BLOG_ID")
headers = {"X-Shopify-Access-Token": token}

# Check recently regenerated articles
check_ids = [691791921470, 691791888702, 691791823166, 691791954238, 690524815678]

needs_rebuild = []

for aid in check_ids:
    url = f"{store}/admin/api/2025-01/blogs/{blog_id}/articles/{aid}.json"
    r = requests.get(url, headers=headers)
    article = r.json().get("article", {})

    title = article.get("title", "")[:50]
    body = article.get("body_html", "") or ""
    meta = article.get("summary_html", "") or ""

    # Count key elements
    img_count = len(re.findall(r"<img[^>]*src=", body))
    source_section = "Sources" in body or "Further Reading" in body
    faq_section = "Frequently Asked" in body or "FAQ" in body
    has_table = "<table" in body.lower()

    status = []
    if img_count < 4:
        status.append(f"images:{img_count}/4")
    if not source_section:
        status.append("NO-SOURCES")
    if not faq_section:
        status.append("NO-FAQ")
    if not has_table:
        status.append("NO-TABLE")
    if not meta:
        status.append("NO-META")

    if status:
        print(f'❌ {aid}: {title} - {" | ".join(status)}')
        needs_rebuild.append(aid)
    else:
        print(f"✅ {aid}: {title}")

if needs_rebuild:
    print(f"\n📋 Articles needing rebuild: {len(needs_rebuild)}")
    print(f'   IDs: {" ".join(map(str, needs_rebuild))}')
