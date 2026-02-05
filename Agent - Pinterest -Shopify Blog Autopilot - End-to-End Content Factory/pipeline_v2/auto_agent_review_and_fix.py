#!/usr/bin/env python3
"""
AUTO AGENT REVIEW AND FIX
=========================
Tß╗▒ ─æß╗Öng qu├⌐t tß║Ñt cß║ú b├ái ─æ├ú publish, ph├ít hiß╗çn lß╗ùi v├á sß╗¡a.

C├íc lß╗ùi cß║ºn detect:
1. Content generic (kh├┤ng ─æ├║ng topic)
2. Images kh├┤ng khß╗¢p topic
3. Images bß╗ï duplicate
4. Missing Pinterest images (cho matched articles)
5. Missing sections (11-section structure)
6. Sources c├│ raw URLs visible

Workflow:
1. Fetch tß║Ñt cß║ú articles tß╗½ Shopify
2. Audit tß╗½ng b├ái theo ti├¬u chuß║⌐n
3. Tß╗▒ sß╗¡a c├íc b├ái lß╗ùi
4. Re-publish vß╗¢i content v├á images ─æ├║ng
"""

import requests
import re
import json
import time
from datetime import datetime
from pathlib import Path
from collections import Counter
import os
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Config
SHOP = os.getenv("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Load matched Pinterest data
SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
MATCHED_FILE = SCRIPT_DIR / "matched_drafts_pinterest.json"


def load_matched_pinterest():
    """Load danh s├ích b├ái ─æ├ú match Pinterest"""
    if MATCHED_FILE.exists():
        with open(MATCHED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {str(item["draft_id"]): item for item in data.get("matched", [])}
    return {}


# Generic phrases to detect off-topic content
GENERIC_PHRASES = [
    "this comprehensive guide",
    "everything you need to know",
    "natural materials vary throughout the year",
    "professional practitioners recommend",
    "achieving consistent results requires attention",
    "once you've perfected small batches",
    "scaling up becomes appealing",
    "mastering precision",
    "measuring cups",
    "dry ingredients",
    "doubling recipes",
    "heat distribution",
    "shelf life 2-4 weeks",
    "shelf life 3-6 months",
]

# Required sections for 11-section structure
REQUIRED_SECTIONS = [
    "direct answer",
    "key conditions",
    "understanding",
    "step-by-step",
    "types and varieties",
    "troubleshooting",
    "pro tips",
    "expert",
    "faq",
    "sources",
    "further reading",
]


def fetch_article(article_id):
    """Fetch article từ Shopify"""
    url = f"https://{SHOP}/admin/api/2025-01/articles/{article_id}.json"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json().get("article")
    return None


def fetch_all_published_articles(limit=250):
    """Fetch tất cả articles đã publish"""
    url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json?limit={limit}&published_status=published"
    articles = []
    while url:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            break
        data = resp.json()
        articles.extend(data.get("articles", []))
        # Get next page
        link_header = resp.headers.get("Link", "")
        if 'rel="next"' in link_header:
            next_url = link_header.split(";")[0].strip("<>")
            url = next_url
        else:
            url = None
    return articles


def audit_content_quality(body_html, title):
    """Kiß╗âm tra content quality, trß║ú vß╗ü list c├íc lß╗ùi"""
    issues = []
    content_lower = body_html.lower() if body_html else ""
    title_lower = title.lower() if title else ""

    # 1. Check generic phrases
    for phrase in GENERIC_PHRASES:
        if phrase.lower() in content_lower:
            issues.append(f"GENERIC: Found '{phrase}'")

    # 2. Check missing sections
    found_sections = []
    for section in REQUIRED_SECTIONS:
        if section in content_lower:
            found_sections.append(section)

    missing = [
        s
        for s in ["direct answer", "step-by-step", "troubleshooting", "faq", "sources"]
        if s not in found_sections
    ]
    if missing:
        issues.append(f"MISSING_SECTIONS: {', '.join(missing)}")

    # 3. Check for off-topic content indicators
    # VD: B├ái vß╗ü vinegar nh╞░ng c├│ content vß╗ü cordage
    topic_keywords = extract_topic_keywords(title)
    off_topic_indicators = [
        ("vinegar", ["cordage", "rope", "twine"]),
        ("plant pot", ["recipe", "cooking", "baking"]),
        ("garden", ["shelf life 2-4 weeks", "dry ingredients"]),
        ("cordage", ["measuring cups", "thermometer", "baking"]),
    ]

    for topic, bad_words in off_topic_indicators:
        if topic in title_lower:
            for bad in bad_words:
                if bad.lower() in content_lower:
                    issues.append(f"OFF_TOPIC: '{bad}' found in '{topic}' article")

    # 4. Check duplicate content indicators
    # Count duplicate paragraphs
    paragraphs = re.findall(r"<p[^>]*>(.+?)</p>", body_html or "", re.DOTALL)
    para_counter = Counter([p.strip()[:100] for p in paragraphs if len(p.strip()) > 50])
    duplicates = [p for p, count in para_counter.items() if count > 1]
    if duplicates:
        issues.append(f"DUPLICATE_CONTENT: {len(duplicates)} duplicate paragraphs")

    return issues


def audit_images(body_html, article_id, matched_pinterest):
    """Kiß╗âm tra images, trß║ú vß╗ü list c├íc lß╗ùi"""
    issues = []

    # Extract all images
    img_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', body_html or "")

    # 1. Check for duplicate images
    url_counter = Counter(img_urls)
    duplicates = [url for url, count in url_counter.items() if count > 1]
    if duplicates:
        issues.append(f"DUPLICATE_IMAGES: {len(duplicates)} duplicate image URLs")

    # 2. Check Pinterest image exists (for matched articles)
    if str(article_id) in matched_pinterest:
        pinterest_match = matched_pinterest[str(article_id)]
        has_pinterest = any("pinimg.com" in url for url in img_urls)
        if not has_pinterest:
            issues.append(
                "MISSING_PINTEREST: Pinterest image missing for matched article"
            )

    # 3. Check image count
    if len(set(img_urls)) < 2:
        issues.append(f"LOW_IMAGES: Only {len(set(img_urls))} unique images")

    # 4. Validate image URLs are accessible
    broken_images = []
    for url in list(set(img_urls))[:5]:  # Check first 5 only
        try:
            resp = requests.head(url, timeout=5, allow_redirects=True)
            if resp.status_code >= 400:
                broken_images.append(url)
        except:
            broken_images.append(url)

    if broken_images:
        issues.append(f"BROKEN_IMAGES: {len(broken_images)} broken image URLs")

    return issues


def audit_sources(body_html):
    """Kiß╗âm tra sources format"""
    issues = []

    # Check for visible raw URLs
    raw_url_pattern = r">https?://[^<]+<|>\S+\.(com|org|edu|gov)[^<]*<"
    raw_urls = re.findall(raw_url_pattern, body_html or "")
    if raw_urls:
        issues.append(f"RAW_URLS: {len(raw_urls)} visible raw URLs in sources")

    # Check sources exist
    if (
        "sources" not in body_html.lower()
        and "further reading" not in body_html.lower()
    ):
        issues.append("NO_SOURCES: Missing sources section")

    return issues


def extract_topic_keywords(title):
    """Extract keywords tß╗½ title ─æß╗â detect off-topic"""
    # Remove common words
    stop_words = [
        "how",
        "to",
        "the",
        "a",
        "an",
        "and",
        "or",
        "for",
        "with",
        "your",
        "complete",
        "guide",
        "faqs",
        "easy",
        "step",
        "by",
        "diy",
        "ideas",
    ]
    words = re.findall(r"\w+", title.lower())
    return [w for w in words if w not in stop_words and len(w) > 2]


def full_audit(article, matched_pinterest):
    """Chß║íy full audit cho 1 article"""
    article_id = article["id"]
    title = article.get("title", "")
    body_html = article.get("body_html", "")

    all_issues = []

    # Content audit
    content_issues = audit_content_quality(body_html, title)
    all_issues.extend(content_issues)

    # Images audit
    image_issues = audit_images(body_html, article_id, matched_pinterest)
    all_issues.extend(image_issues)

    # Sources audit
    source_issues = audit_sources(body_html)
    all_issues.extend(source_issues)

    return {
        "id": article_id,
        "title": title,
        "handle": article.get("handle", ""),
        "url": f"https://therike.com/blogs/sustainable-living/{article.get('handle', '')}",
        "issues": all_issues,
        "issue_count": len(all_issues),
        "status": "FAIL" if all_issues else "PASS",
    }


def run_full_audit():
    """Chß║íy audit cho tß║Ñt cß║ú articles"""
    print("=" * 60)
    print("AUTO AGENT REVIEW - FULL AUDIT")
    print("=" * 60)

    # Load matched Pinterest data
    matched_pinterest = load_matched_pinterest()
    print(f"Γ£à Loaded {len(matched_pinterest)} matched Pinterest articles")

    # Fetch all published articles
    print("\n≡ƒôÑ Fetching published articles from Shopify...")
    articles = fetch_all_published_articles()
    print(f"Γ£à Found {len(articles)} published articles")

    # Audit each article
    results = []
    failed = []
    passed = []

    print("\n≡ƒöì Auditing articles...")
    for i, article in enumerate(articles):
        result = full_audit(article, matched_pinterest)
        results.append(result)

        if result["status"] == "FAIL":
            failed.append(result)
        else:
            passed.append(result)

        # Progress
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(articles)} articles audited")

    # Summary
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    print(f"Γ£à PASSED: {len(passed)} articles")
    print(f"Γ¥î FAILED: {len(failed)} articles")

    # Group issues
    issue_types = Counter()
    for result in failed:
        for issue in result["issues"]:
            issue_type = issue.split(":")[0]
            issue_types[issue_type] += 1

    print("\n≡ƒôè Issue breakdown:")
    for issue_type, count in issue_types.most_common():
        print(f"  {issue_type}: {count}")

    # Show failed articles
    if failed:
        print("\nΓ¥î Failed articles:")
        for result in failed[:20]:  # Show first 20
            print(f"\n  {result['title'][:50]}...")
            print(f"    URL: {result['url']}")
            for issue in result["issues"]:
                print(f"    - {issue}")

    # Save results
    output_file = Path(__file__).parent / "audit_results_full.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "total": len(results),
                "passed": len(passed),
                "failed": len(failed),
                "issue_types": dict(issue_types),
                "failed_articles": failed,
                "passed_articles": passed,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\n≡ƒÆ╛ Results saved to: {output_file}")

    return failed


def run_audit_21_matched():
    """Audit chß╗ë 21 b├ái matched Pinterest"""
    print("=" * 60)
    print("AUDIT 21 MATCHED PINTEREST ARTICLES")
    print("=" * 60)

    matched_pinterest = load_matched_pinterest()
    print(f"Γ£à Loaded {len(matched_pinterest)} matched Pinterest articles")

    failed = []
    passed = []

    for article_id, pinterest_data in matched_pinterest.items():
        article = fetch_article(article_id)
        if not article:
            print(f"ΓÜá∩╕Å Could not fetch article {article_id}")
            continue

        result = full_audit(article, matched_pinterest)

        if result["status"] == "FAIL":
            failed.append(result)
            print(f"\nΓ¥î FAIL: {result['title'][:40]}...")
            for issue in result["issues"]:
                print(f"    - {issue}")
        else:
            passed.append(result)
            print(f"Γ£à PASS: {result['title'][:40]}...")

    print("\n" + "=" * 60)
    print(f"SUMMARY: {len(passed)} PASSED, {len(failed)} FAILED")
    print("=" * 60)

    return failed


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--matched":
        # Audit only 21 matched Pinterest
        run_audit_21_matched()
    else:
        # Full audit
        run_full_audit()
