#!/usr/bin/env python3
"""
Comprehensive article scanner - Check for:
1. Broken images (404, missing src)
2. Generic template content
3. Content quality issues (too short, spam patterns)
4. Missing sections
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

SHOPIFY_STORE = "https://" + os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID")

# Generic content patterns from ai_orchestrator
GENERIC_PATTERNS = [
    r"Central to [^<]{10,80} and used throughout the content below",
    r"The sources listed here provide the foundation",
    r"These frequently asked questions address common",
    r"href=['\"]https?://www\.(epa|usda|cdc|nih|fda)\.gov/?['\"]",
    r"Based on the context of [^<]{10,100}, here are some",
    r"This section covers essential terminology",
]


def get_all_articles(limit=50):
    """Fetch recent articles from Shopify."""
    url = f"{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
    params = {"limit": limit, "fields": "id,title,handle,body_html,image,published_at"}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("articles", [])
    return []


def check_images(body_html: str) -> dict:
    """Check for image issues."""
    issues = []
    soup = BeautifulSoup(body_html, "html.parser")
    images = soup.find_all("img")

    broken_count = 0
    for img in images:
        src = img.get("src", "")
        if not src:
            issues.append("Image with empty src")
            broken_count += 1
            continue

        # Check if image is accessible
        try:
            response = requests.head(src, timeout=5, allow_redirects=True)
            if response.status_code >= 400:
                issues.append(
                    f"Broken image (HTTP {response.status_code}): {src[:60]}..."
                )
                broken_count += 1
        except Exception as e:
            issues.append(f"Cannot reach image: {src[:60]}...")
            broken_count += 1

    return {"total": len(images), "broken": broken_count, "issues": issues}


def check_generic_content(body_html: str) -> dict:
    """Check for generic template content."""
    issues = []

    for pattern in GENERIC_PATTERNS:
        if re.search(pattern, body_html, re.IGNORECASE):
            issues.append(f"Generic pattern found: {pattern[:50]}...")

    return {"has_generic": len(issues) > 0, "issues": issues}


def check_content_quality(body_html: str, title: str) -> dict:
    """Check for content quality issues."""
    issues = []
    soup = BeautifulSoup(body_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)

    # Word count
    words = text.split()
    word_count = len(words)

    if word_count < 500:
        issues.append(f"Very short content: only {word_count} words")
    elif word_count < 800:
        issues.append(f"Short content: {word_count} words (aim for 1500+)")

    # Check for title spam (repeated title fragments)
    title_words = [w for w in title.lower().split() if len(w) > 4]
    if title_words:
        for word in title_words:
            count = text.lower().count(word)
            if count > 30:
                issues.append(f"Title word '{word}' repeated {count} times (spam?)")

    # Check for structure
    h2_count = len(soup.find_all("h2"))
    h3_count = len(soup.find_all("h3"))

    if h2_count == 0:
        issues.append("No H2 headings found")
    if h2_count < 3:
        issues.append(f"Only {h2_count} H2 headings (weak structure)")

    # Check for lists
    list_count = len(soup.find_all(["ul", "ol"]))
    if list_count == 0:
        issues.append("No lists found (may need better formatting)")

    return {
        "word_count": word_count,
        "h2_count": h2_count,
        "h3_count": h3_count,
        "list_count": list_count,
        "issues": issues,
    }


def scan_article(article: dict) -> dict:
    """Comprehensive scan of a single article."""
    title = article.get("title", "Unknown")
    body = article.get("body_html", "")
    article_id = article.get("id")
    published = article.get("published_at")

    result = {
        "id": article_id,
        "title": title[:50],
        "published": bool(published),
        "issues": [],
        "severity": "OK",
    }

    if not body:
        result["issues"].append("EMPTY BODY")
        result["severity"] = "CRITICAL"
        return result

    # Check images
    img_check = check_images(body)
    if img_check["broken"] > 0:
        result["issues"].append(
            f"BROKEN IMAGES: {img_check['broken']}/{img_check['total']}"
        )
        for issue in img_check["issues"][:3]:  # First 3 image issues
            result["issues"].append(f"  - {issue}")
        result["severity"] = "HIGH" if img_check["broken"] > 2 else "MEDIUM"

    # Check generic content
    generic_check = check_generic_content(body)
    if generic_check["has_generic"]:
        result["issues"].append("GENERIC CONTENT DETECTED")
        result["severity"] = "HIGH"

    # Check content quality
    quality_check = check_content_quality(body, title)
    for issue in quality_check["issues"]:
        result["issues"].append(issue)
        if "spam" in issue.lower():
            result["severity"] = "CRITICAL"

    result["word_count"] = quality_check["word_count"]

    if not result["issues"]:
        result["severity"] = "OK"

    return result


def main():
    print("=" * 70)
    print("COMPREHENSIVE ARTICLE SCANNER")
    print("=" * 70)
    print()

    print("Fetching articles from Shopify...")
    articles = get_all_articles(limit=50)
    print(f"Found {len(articles)} articles to scan")
    print()

    results = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "OK": []}

    for i, article in enumerate(articles):
        print(
            f"[{i+1}/{len(articles)}] Scanning: {article.get('title', 'Unknown')[:40]}...",
            end=" ",
        )
        result = scan_article(article)
        results[result["severity"]].append(result)
        print(f"[{result['severity']}]")

    print()
    print("=" * 70)
    print("SCAN RESULTS SUMMARY")
    print("=" * 70)

    print(f"\n✅ OK: {len(results['OK'])} articles")
    print(f"⚠️  MEDIUM: {len(results['MEDIUM'])} articles")
    print(f"🔶 HIGH: {len(results['HIGH'])} articles")
    print(f"🔴 CRITICAL: {len(results['CRITICAL'])} articles")

    # Show details for problematic articles
    for severity in ["CRITICAL", "HIGH", "MEDIUM"]:
        if results[severity]:
            print(f"\n{'='*70}")
            print(f"[{severity}] ISSUES ({len(results[severity])} articles)")
            print("=" * 70)
            for result in results[severity]:
                print(f"\n📰 {result['title']}")
                print(f"   ID: {result['id']}")
                print(f"   Published: {'Yes' if result['published'] else 'No'}")
                print(f"   Words: {result.get('word_count', 'N/A')}")
                for issue in result["issues"]:
                    print(f"   ❌ {issue}")

    # Save results to file
    import json

    with open("scan_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to scan_results.json")

    # Create list of articles needing fixes
    needs_fix = []
    for severity in ["CRITICAL", "HIGH"]:
        for result in results[severity]:
            needs_fix.append(
                {
                    "id": result["id"],
                    "title": result["title"],
                    "severity": severity,
                    "issues": result["issues"],
                }
            )

    if needs_fix:
        with open("articles_needing_fix.json", "w", encoding="utf-8") as f:
            json.dump(needs_fix, f, indent=2, ensure_ascii=False)
        print(f"Articles needing fix saved to articles_needing_fix.json")

        print(f"\n{'='*70}")
        print(f"ARTICLES NEEDING WORKFLOW FIXES: {len(needs_fix)}")
        print("=" * 70)
        for item in needs_fix:
            print(f"  {item['id']}: {item['title']} [{item['severity']}]")

    return needs_fix


if __name__ == "__main__":
    needs_fix = main()
