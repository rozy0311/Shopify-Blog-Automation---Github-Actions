#!/usr/bin/env python3
"""Scan all published articles for quality issues."""
import os
import sys
import requests
import re

sys.path.insert(
    0,
    "Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory/pipeline_v2",
)
from dotenv import load_dotenv

load_dotenv(
    "Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory/.env",
    override=True,
)

shop = os.environ.get("SHOPIFY_STORE_DOMAIN", "the-rike-inc.myshopify.com")
token = os.environ.get("SHOPIFY_ACCESS_TOKEN")
blog_id = os.environ.get("SHOPIFY_BLOG_ID", "108441862462")
api_version = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

# Paginate to get all articles
all_articles = []
url = f"https://{shop}/admin/api/{api_version}/blogs/{blog_id}/articles.json?status=published&limit=250"
headers = {"X-Shopify-Access-Token": token}

while url:
    resp = requests.get(url, headers=headers)
    articles = resp.json().get("articles", [])
    all_articles.extend(articles)

    # Check for next page
    link_header = resp.headers.get("Link", "")
    if 'rel="next"' in link_header:
        match = re.search(r'<([^>]+)>; rel="next"', link_header)
        url = match.group(1) if match else None
    else:
        url = None

print(f"Total published: {len(all_articles)}")

# Categorize
low = [
    (a["id"], a["title"][:50], len(a.get("body_html", "")))
    for a in all_articles
    if len(a.get("body_html", "")) < 12000
]
med = [
    (a["id"], a["title"][:50], len(a.get("body_html", "")))
    for a in all_articles
    if 12000 <= len(a.get("body_html", "")) < 18000
]
high = [
    (a["id"], a["title"][:50], len(a.get("body_html", "")))
    for a in all_articles
    if len(a.get("body_html", "")) >= 18000
]

print(f"\n📊 QUALITY DISTRIBUTION:")
print(
    f"  🔴 LOW (<12K chars):    {len(low):>3} ({100*len(low)/len(all_articles):.1f}%) - NEED REGENERATE"
)
print(
    f"  🟡 MEDIUM (12-18K):     {len(med):>3} ({100*len(med)/len(all_articles):.1f}%)"
)
print(
    f"  🟢 HIGH (>18K chars):   {len(high):>3} ({100*len(high)/len(all_articles):.1f}%)"
)

print(f"\n🔴 TOP 20 LOWEST QUALITY:")
for aid, title, length in sorted(low, key=lambda x: x[2])[:20]:
    print(f"  {aid}: {length:>6,} chars - {title}")

print(f"\n🟢 TOP 30 HIGHEST QUALITY (>18K):")
for aid, title, length in sorted(high, key=lambda x: -x[2])[:30]:
    print(f"  {aid}: {length:>6,} chars - {title}")

# Stats for high quality
if high:
    lengths = [x[2] for x in high]
    print(f"\n📈 HIGH QUALITY STATS:")
    print(f"  Average: {sum(lengths)//len(lengths):,} chars")
    print(f"  Max: {max(lengths):,} chars")
    print(f"  Min: {min(lengths):,} chars")

# Save low quality IDs
low_ids = [str(a[0]) for a in sorted(low, key=lambda x: x[2])]
with open("low_quality_ids.txt", "w") as f:
    f.write("\n".join(low_ids))
print(f"\n✅ Saved {len(low_ids)} IDs to low_quality_ids.txt")
