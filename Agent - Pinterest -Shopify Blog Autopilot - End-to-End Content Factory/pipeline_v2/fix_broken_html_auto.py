#!/usr/bin/env python3
"""
FIX BROKEN HTML LINKS - Auto repair exposed HTML attributes
============================================================
Fixes patterns like:
- domain.com/path" rel="nofollow noopener"> ΓåÆ proper <a> tags
- Exposed URLs in visible text
"""

import os
import re
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_paths = [
    Path(__file__).parent.parent.parent.parent / ".env",
    Path(__file__).parent.parent.parent / ".env",
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break
load_dotenv()

SHOP = "the-rike-inc.myshopify.com"
TOKEN = os.environ.get("SHOPIFY_TOKEN") or os.environ.get("SHOPIFY_ACCESS_TOKEN")
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}


def get_article(article_id):
    url = f"https://{SHOP}/admin/api/2025-01/articles/{article_id}.json"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json().get("article")
    return None


def fix_broken_html(html):
    """Fix broken HTML patterns"""
    fixed = html
    changes = []

    # Pattern 1: Exposed URL with rel attribute at end
    # e.g., lomondviewnursery.com/how-to..." rel="nofollow noopener">
    pattern1 = r'([a-zA-Z0-9-]+\.(com|org|net|edu|gov|io)/[^\s"<>]+)"\s*rel="[^"]*">'
    matches1 = re.findall(pattern1, fixed, re.IGNORECASE)
    if matches1:
        for match in matches1:
            url = match[0]
            # This is broken - the URL should be inside an <a> tag
            # Try to find and fix the full broken pattern
            old_pattern = re.escape(url) + r'"\s*rel="[^"]*">'
            # Create proper link
            domain = url.split("/")[0]
            new_link = f'<a href="https://{url}" target="_blank" rel="nofollow noopener">{domain}</a>'
            if re.search(old_pattern, fixed):
                fixed = re.sub(old_pattern, new_link, fixed, count=1)
                changes.append(f"Fixed broken link: {url[:50]}")

    # Pattern 2: Raw URL in text (not in href)
    # Find URLs that appear outside of href="" but still as visible text
    # This is tricky - we need to not break existing proper links

    # Pattern 3: Clean up orphaned rel="" attributes
    fixed = re.sub(r'\s*rel="[^"]*">\s*(?=[^<]*<)', "> ", fixed)

    # Pattern 4: Fix double >> or orphaned >
    fixed = re.sub(r">\s*>", ">", fixed)

    return fixed, changes


def update_article(article_id, html):
    url = f"https://{SHOP}/admin/api/2025-01/articles/{article_id}.json"
    payload = {"article": {"id": article_id, "body_html": html}}
    resp = requests.put(url, headers=HEADERS, json=payload)
    return resp.status_code == 200


def main():
    # Load audit results
    audit_file = Path(__file__).parent / "post_publish_audit.json"
    if not audit_file.exists():
        print("Γ¥î Run post_publish_audit.py first")
        return

    with open(audit_file, "r", encoding="utf-8") as f:
        audit = json.load(f)

    # Filter for broken_html_link issues
    broken_articles = [
        a
        for a in audit["articles_needing_fix"]
        if any(i["type"] == "broken_html_link" for i in a["issues"])
    ]

    print(f"Found {len(broken_articles)} articles with broken HTML links\n")

    fixed_count = 0
    for art in broken_articles:
        article_id = art["id"]
        title = art["title"]

        print(f"Processing: {title[:50]}")

        article = get_article(article_id)
        if not article:
            print(f"  Γ¥î Could not fetch article")
            continue

        html = article.get("body_html", "")
        fixed_html, changes = fix_broken_html(html)

        if changes:
            print(f"  Changes: {changes}")
            if update_article(article_id, fixed_html):
                print(f"  Γ£à Fixed and updated")
                fixed_count += 1
            else:
                print(f"  Γ¥î Failed to update")
        else:
            print(f"  ΓÜá∩╕Å No patterns matched - may need manual review")

    print(f"\n{'='*40}")
    print(f"Fixed {fixed_count}/{len(broken_articles)} articles")


if __name__ == "__main__":
    main()
