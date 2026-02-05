#!/usr/bin/env python3
"""
Classify articles into:
1. TEMPLATE GARBAGE - needs full regeneration (title repeated as gibberish)
2. GENERIC CONTENT - needs strip_generic_sections
3. BROKEN IMAGES - needs image regeneration
4. OK - no issues
"""

import os
import json
import re
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

SHOPIFY_STORE = "https://" + os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID")

GENERIC_PATTERNS = [
    r"Central to [^<]{10,80} and used throughout the content below",
    r"The sources listed here provide the foundation",
    r"These frequently asked questions address common",
]


def get_all_articles(limit=50):
    """Fetch recent articles from Shopify."""
    url = f"{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
    params = {"limit": limit, "fields": "id,title,handle,body_html,published_at"}

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("articles", [])
    return []


def is_template_garbage(title: str, body: str) -> bool:
    """Detect if article has template garbage content."""
    soup = BeautifulSoup(body, "html.parser")
    text = soup.get_text(" ", strip=True).lower()

    # Pattern 1: "works best when you" + "key conditions at a glance"
    if "works best when you" in text and "key conditions at a glance" in text:
        return True

    # Pattern 2: Title repeated as phrase > 5 times
    title_clean = re.sub(r"[^a-z0-9 ]", "", title.lower())
    title_words = [w for w in title_clean.split() if len(w) > 4]

    if len(title_words) >= 3:
        # Check multi-word title phrase repetition
        title_phrase = " ".join(title_words[:4])
        if text.count(title_phrase) > 5:
            return True

    # Pattern 3: "direct answer" at start with title repeated
    if text.startswith("direct answer") and title.lower()[:20] in text[:200]:
        # Check if this is garbage structure
        if "align steps" in text or "adjust one variable" in text:
            return True

    return False


def has_generic_content(body: str) -> bool:
    """Check for generic template sections."""
    for pattern in GENERIC_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            return True
    return False


def check_images(body: str) -> int:
    """Return count of broken images."""
    soup = BeautifulSoup(body, "html.parser")
    images = soup.find_all("img")
    broken = 0

    for img in images:
        src = img.get("src", "")
        if not src:
            broken += 1
            continue
        try:
            response = requests.head(src, timeout=5, allow_redirects=True)
            if response.status_code >= 400:
                broken += 1
        except:
            broken += 1

    return broken


def classify_articles():
    """Classify all articles."""
    print("Fetching articles...")
    articles = get_all_articles(limit=50)
    print(f"Found {len(articles)} articles\n")

    results = {
        "template_garbage": [],
        "generic_content": [],
        "broken_images": [],
        "ok": [],
    }

    for i, article in enumerate(articles):
        aid = article.get("id")
        title = article.get("title", "")
        body = article.get("body_html", "")

        print(f"[{i+1}/{len(articles)}] {title[:40]}...", end=" ")

        # Check for template garbage first (most severe)
        if is_template_garbage(title, body):
            results["template_garbage"].append(
                {"id": aid, "title": title, "issue": "TEMPLATE_GARBAGE"}
            )
            print("[GARBAGE]")
            continue

        # Check for generic content
        if has_generic_content(body):
            results["generic_content"].append(
                {"id": aid, "title": title, "issue": "GENERIC_CONTENT"}
            )
            print("[GENERIC]")
            continue

        # Check for broken images
        broken = check_images(body)
        if broken > 0:
            results["broken_images"].append(
                {"id": aid, "title": title, "issue": f"BROKEN_IMAGES:{broken}"}
            )
            print(f"[BROKEN_IMG:{broken}]")
            continue

        results["ok"].append({"id": aid, "title": title})
        print("[OK]")

    return results


def main():
    print("=" * 70)
    print("ARTICLE CLASSIFICATION")
    print("=" * 70)
    print()

    results = classify_articles()

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"\n🔴 TEMPLATE GARBAGE (need full regen): {len(results['template_garbage'])}"
    )
    for item in results["template_garbage"]:
        print(f"   {item['id']}: {item['title'][:45]}")

    print(f"\n🔶 GENERIC CONTENT (need strip): {len(results['generic_content'])}")
    for item in results["generic_content"]:
        print(f"   {item['id']}: {item['title'][:45]}")

    print(f"\n🔵 BROKEN IMAGES: {len(results['broken_images'])}")
    for item in results["broken_images"]:
        print(f"   {item['id']}: {item['title'][:45]} ({item['issue']})")

    print(f"\n✅ OK: {len(results['ok'])}")

    # Save results
    with open("article_classification.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nResults saved to article_classification.json")

    # Create list of IDs needing regeneration
    regen_ids = [item["id"] for item in results["template_garbage"]]
    if regen_ids:
        with open("articles_need_regen.txt", "w") as f:
            f.write("\n".join(str(aid) for aid in regen_ids))
        print(
            f"Regeneration IDs saved to articles_need_regen.txt ({len(regen_ids)} articles)"
        )

    return results


if __name__ == "__main__":
    main()
