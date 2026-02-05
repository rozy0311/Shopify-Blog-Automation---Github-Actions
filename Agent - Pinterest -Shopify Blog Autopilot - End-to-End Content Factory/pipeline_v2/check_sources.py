#!/usr/bin/env python3
"""Check sources section of an article."""
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

store = "https://" + os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
token = os.getenv("SHOPIFY_ACCESS_TOKEN")
blog_id = os.getenv("SHOPIFY_BLOG_ID")
headers = {"X-Shopify-Access-Token": token}

aid = 691731562814
url = f"{store}/admin/api/2025-01/blogs/{blog_id}/articles/{aid}.json"
r = requests.get(url, headers=headers)
article = r.json().get("article", {})
body = article.get("body_html", "")

# Find sources section
sources_match = re.search(r"<h2[^>]*>.*Sources.*</h2>", body, re.IGNORECASE)
if sources_match:
    print("Sources H2 found at:", sources_match.start())
    # Get content after sources heading
    sources_content = body[sources_match.end() :]
    # Find next H2
    next_h2 = re.search(r"<h2", sources_content, re.IGNORECASE)
    if next_h2:
        sources_content = sources_content[: next_h2.start()]

    # Count links
    links = re.findall(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
        sources_content,
        re.IGNORECASE,
    )
    print(f"Found {len(links)} links in sources section:")
    for url, text in links[:10]:
        print(f"  - {text[:50]}: {url[:50]}...")

    # Show raw sources content
    print("\n=== RAW SOURCES SECTION ===")
    print(sources_content[:1500])
else:
    print("NO sources section found!")
    # Check for any h2 headings
    h2s = re.findall(r"<h2[^>]*>([^<]+)</h2>", body, re.IGNORECASE)
    print("H2 headings found:", h2s)
