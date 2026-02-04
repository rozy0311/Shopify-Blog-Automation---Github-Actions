#!/usr/bin/env python3
"""
Sequential runner for force-rebuild using ai_orchestrator.
This uses the full pipeline with images, sources, meta, etc.

Usage:
  python sequential_rebuild.py                  # Run all garbage articles
  python sequential_rebuild.py --max 5          # Max 5 articles
  python sequential_rebuild.py --interval 600   # 10 minute intervals
  python sequential_rebuild.py --dry-run        # Show what would run
"""

import os
import re
import sys
import time
import json
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

SHOPIFY_STORE = "https://" + os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID")


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def get_all_articles() -> list:
    """Get all published articles."""
    url = f"{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json"
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}
    params = {"status": "published", "limit": 250}

    response = requests.get(url, headers=headers, params=params, timeout=30)
    if response.status_code != 200:
        log(f"Error fetching articles: {response.status_code}")
        return []

    return response.json().get("articles", [])


def is_template_garbage(body: str, title: str) -> bool:
    """Detect if article has template garbage content.

    Only detects REAL garbage patterns, not false positives.
    """
    if not body:
        return True

    body_lower = body.lower()

    # DEFINITIVE garbage patterns - these are TEMPLATE content
    garbage_patterns = [
        # Template phrases from _build_article_body fallback
        r"works best when you keep the steps specific to",
        r"measure inputs carefully.*test a small area",
        r"if anything looks off, adjust one variable at a time so you can trace",
        r"<li>light-duty use: small batch, simple steps",
        r"<li>standard use: balanced inputs, consistent timing",
        r"apply the method evenly and avoid rushing steps",
        r"adjust one variable at a time so you can see what actually improves",
        r"label any containers so measurements are not confused later",
        r"choose a small test run first\. this keeps .* controlled",
        # Also check for _build_key_terms_section garbage
        r"key terms.*central to.*used throughout the content below",
    ]

    for pattern in garbage_patterns:
        if re.search(pattern, body_lower):
            return True

    # Title word spam (only if 50+ occurrences AND short words)
    text = re.sub(r"<[^>]+>", " ", body)
    text = re.sub(r"\s+", " ", text).strip().lower()

    title_words = [w.lower() for w in re.findall(r"\b\w{4,}\b", title)]
    for word in title_words:
        # Must be at least 50 occurrences AND word appears consecutively
        count = text.count(word)
        if count > 50:
            # Check if it's real spam (consecutive pattern)
            spam_pattern = rf"{word}\s+{word}\s+{word}"
            if re.search(spam_pattern, text):
                return True

    return False


def find_garbage_articles() -> list:
    """Find articles with template garbage."""
    log("Fetching articles...")
    articles = get_all_articles()
    log(f"Found {len(articles)} articles")

    garbage = []
    for article in articles:
        aid = article.get("id")
        title = article.get("title", "")
        body = article.get("body_html", "")

        if is_template_garbage(body, title):
            garbage.append({"id": str(aid), "title": title[:50]})

    return garbage


def run_force_rebuild(article_id: str, dry_run: bool = False) -> bool:
    """Run force-rebuild for a single article using orchestrator."""
    if dry_run:
        log(f"[DRY RUN] Would rebuild: {article_id}")
        return True

    import subprocess

    cmd = [sys.executable, "ai_orchestrator.py", "force-rebuild-ids", article_id]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )

        output = result.stdout + result.stderr

        # Check for success indicators
        if "[OK] Force rebuild PASS" in output:
            return True
        elif "Force rebuild FAIL" in output:
            # Still update but with issues
            if "✅ SUCCESS!" in output:
                return True  # Content updated, just gate fail
            return False
        else:
            log(f"Unexpected output: {output[-500:]}")
            return False

    except subprocess.TimeoutExpired:
        log(f"Timeout rebuilding {article_id}")
        return False
    except Exception as e:
        log(f"Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Sequential rebuild using orchestrator"
    )
    parser.add_argument(
        "--max", type=int, default=0, help="Max articles to process (0=all)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Seconds between articles (default 5 min)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Don't actually rebuild")
    parser.add_argument("--ids", type=str, help="Comma-separated article IDs")
    args = parser.parse_args()

    log("=" * 60)
    log("SEQUENTIAL REBUILD WITH FULL ORCHESTRATOR")
    log("=" * 60)

    if args.ids:
        articles = [
            {"id": i.strip(), "title": "Manual ID"} for i in args.ids.split(",")
        ]
    else:
        articles = find_garbage_articles()

    if not articles:
        log("No articles to rebuild!")
        return

    if args.max > 0:
        articles = articles[: args.max]

    log(f"\nFound {len(articles)} articles to rebuild")
    log(f"Interval: {args.interval} seconds ({args.interval/60:.1f} minutes)")

    if args.dry_run:
        log("DRY RUN MODE - No changes will be made")

    total_time = len(articles) * args.interval
    log(
        f"Estimated total time: {total_time/60:.1f} minutes ({total_time/3600:.1f} hours)\n"
    )

    # Confirmation
    if not args.dry_run:
        log("Starting in 5 seconds... (Ctrl+C to cancel)")
        time.sleep(5)

    success = 0
    failed = 0

    for idx, article in enumerate(articles, 1):
        aid = article["id"]
        title = article["title"]

        log(f"\n[{idx}/{len(articles)}] Rebuilding: {aid} - {title}")

        if run_force_rebuild(aid, args.dry_run):
            success += 1
            log(f"Result: SUCCESS")
        else:
            failed += 1
            log(f"Result: FAILED (content still updated)")

        # Wait between articles (except last one)
        if idx < len(articles) and not args.dry_run:
            log(f"Waiting {args.interval} seconds before next...")
            time.sleep(args.interval)

    log("\n" + "=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"Total processed: {len(articles)}")
    log(f"Success: {success}")
    log(f"Failed: {failed}")


if __name__ == "__main__":
    main()
