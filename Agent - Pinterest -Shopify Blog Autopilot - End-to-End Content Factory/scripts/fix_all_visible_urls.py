#!/usr/bin/env python3
"""
Fix all articles: Convert visible URL links to hidden links
FROM: <a href="url">url.com</a> or plain text "url.com"
TO: <a href="url">Source Name</a>

This keeps links clickable but hides the URL, showing source name instead
"""

import requests
import re
import json

# === CONFIGURATION ===
SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"

# Mapping of URLs to proper source names
URL_TO_SOURCE = {
    "precedenceresearch.com": "Precedence Research",
    "mordorintelligence.com": "Mordor Intelligence",
    "visionresearchreports.com": "Vision Research Reports",
    "gminsights.com": "Global Market Insights",
    "coherentmarketinsights.com": "Coherent Market Insights",
    "ucihealth.org": "UCI Health",
    "nourishingmeals.com": "Nourishing Meals",
    "gatorcare.org": "GatorCare",
    "modernfarmer.com": "Modern Farmer",
    "agresearchmag.ars.usda.gov": "USDA AgResearch Magazine",
    "ncsu.edu": "NC State Extension",
    "ces.ncsu.edu": "NC State Cooperative Extension",
    "nih.gov": "National Institutes of Health",
    "ncbi.nlm.nih.gov": "NIH PubMed",
    "pubmed.ncbi": "PubMed",
    "pmc.ncbi": "NIH PMC",
    "epa.gov": "EPA",
    "madesafe.org": "MADE SAFE",
    "pexels.com": "Pexels",
    "mdpi.com": "MDPI Journal",
    "herbalgram.org": "HerbalGram",
    "doi.org": "Research Study",
    "imarcgroup.com": "IMARC Group",
    "yahoo.com": "Yahoo Finance",
    "foodnavigator": "Food Navigator",
    "frontiersin.org": "Frontiers Journal",
    "sciencedirect.com": "ScienceDirect",
    "nature.com": "Nature",
    "springer.com": "Springer",
    "wiley.com": "Wiley",
    "tandfonline.com": "Taylor & Francis",
    "jstor.org": "JSTOR",
}


def get_headers():
    return {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}


def fetch_all_articles(limit=100):
    """Fetch all articles from blog"""
    all_articles = []
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json?limit={limit}"

    while url:
        resp = requests.get(url, headers=get_headers(), timeout=30)
        if resp.status_code != 200:
            break

        data = resp.json()
        articles = data.get("articles", [])
        all_articles.extend(articles)

        # Check for pagination
        link_header = resp.headers.get("Link", "")
        if 'rel="next"' in link_header:
            # Extract next URL
            match = re.search(r'<([^>]+)>; rel="next"', link_header)
            if match:
                url = match.group(1)
            else:
                break
        else:
            break

    return all_articles


def get_source_name(url):
    """Get source name from URL"""
    for domain, name in URL_TO_SOURCE.items():
        if domain in url.lower():
            return name

    # Try to extract domain name
    match = re.search(r"https?://(?:www\.)?([^/]+)", url)
    if match:
        domain = match.group(1)
        # Clean up domain
        parts = domain.split(".")
        if len(parts) >= 2:
            name = parts[-2].title()
            if name.lower() not in ["com", "org", "net", "gov", "edu"]:
                return name

    return "Source"


def fix_visible_links(html_content):
    """
    Fix links that show URL as text
    Convert: <a href="url">visible-url.com</a>
    To: <a href="url">Source Name</a>
    """
    if not html_content:
        return html_content, 0

    changes = 0

    # Pattern 1: Links where text contains domain-like patterns
    # <a href="...">text with .com/.org/.gov/etc</a>
    def replace_link(match):
        nonlocal changes
        full_tag = match.group(0)
        href = match.group(1)
        text = match.group(2)

        # Check if text looks like a URL
        if re.search(r"\.(com|org|net|gov|edu|io|co)", text.lower()):
            source_name = get_source_name(href)
            changes += 1
            return f'<a href="{href}" target="_blank" rel="noopener">{source_name}</a>'

        return full_tag

    # Find and fix links with URL-like text
    pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*(?:\.com|\.org|\.net|\.gov|\.edu|\.io)[^<]*)</a>'
    html_content = re.sub(pattern, replace_link, html_content, flags=re.IGNORECASE)

    # Pattern 2: References section - convert URL text to source names
    # Look for: <li>...text...<a href="url">url.domain.com</a></li>
    pattern2 = r'(<li>[^<]*<a[^>]*href=["\'])([^"\']+)(["\'][^>]*>)([^<]*(?:\.com|\.org|\.gov|\.edu)[^<]*)(</a>)'

    def replace_ref(match):
        nonlocal changes
        pre = match.group(1)
        href = match.group(2)
        mid = match.group(3)
        text = match.group(4)
        post = match.group(5)

        if re.search(r"\.(com|org|gov|edu)", text.lower()):
            source_name = get_source_name(href)
            changes += 1
            return f"{pre}{href}{mid}{source_name}{post}"

        return match.group(0)

    html_content = re.sub(pattern2, replace_ref, html_content, flags=re.IGNORECASE)

    return html_content, changes


def update_article(article_id, new_body_html):
    """Update article with fixed HTML"""
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"

    data = {"article": {"id": article_id, "body_html": new_body_html}}

    resp = requests.put(url, headers=get_headers(), json=data, timeout=30)
    return resp.status_code == 200


def has_visible_urls(html_content):
    """Check if article has visible URL text in links"""
    if not html_content:
        return False

    # Look for links with URL-like text
    pattern = r"<a[^>]*>[^<]*(?:\.com|\.org|\.gov|\.edu|\.net)[^<]*</a>"
    matches = re.findall(pattern, html_content, re.IGNORECASE)

    for match in matches:
        # Extract text
        text_match = re.search(r">([^<]+)<", match)
        if text_match:
            text = text_match.group(1)
            # Check if it's a URL-like text (not just mentions "website.com" in prose)
            if re.search(r"^[a-zA-Z0-9.-]+\.(com|org|gov|edu|net)", text.strip()):
                return True

    return False


def main():
    print("=" * 60)
    print("FIXING VISIBLE URL LINKS IN ARTICLES")
    print("Converting URL text to Source Names")
    print("=" * 60)

    # Fetch all articles
    print("\nFetching articles...")
    articles = fetch_all_articles(250)
    print(f"Found {len(articles)} articles")

    fixed_count = 0
    checked_count = 0

    for article in articles:
        article_id = article["id"]
        title = article["title"]
        body_html = article.get("body_html", "")

        checked_count += 1

        if has_visible_urls(body_html):
            print(f"\n🔧 Checking: {title[:50]}...")

            new_body, changes = fix_visible_links(body_html)

            if changes > 0:
                print(f"   Found {changes} visible URLs to fix")

                if update_article(article_id, new_body):
                    print(f"   ✅ Fixed!")
                    fixed_count += 1
                else:
                    print(f"   ❌ Failed to update")

    print("\n" + "=" * 60)
    print(f"SUMMARY:")
    print(f"  📊 Checked: {checked_count} articles")
    print(f"  ✅ Fixed: {fixed_count} articles")
    print("=" * 60)


if __name__ == "__main__":
    main()
