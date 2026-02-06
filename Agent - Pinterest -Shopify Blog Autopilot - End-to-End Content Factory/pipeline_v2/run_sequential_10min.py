#!/usr/bin/env python3
"""
Run auto-fix-sequential workflow for multiple articles with delay between each.
This triggers the GitHub Actions workflow for each article with a configurable interval.

Usage:
  python run_sequential_10min.py                    # Run for next articles in queue
  python run_sequential_10min.py --max 5            # Run max 5 articles
  python run_sequential_10min.py --interval 600    # 10 minute intervals (default)
  python run_sequential_10min.py --dry-run          # Print what would run
"""

import os
import sys
import time
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime

# Load env
try:
    from dotenv import load_dotenv

    for p in [Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if p.exists():
            load_dotenv(p)
            break
except ImportError:
    pass


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def get_articles_needing_fix() -> list:
    """Get list of article IDs that need fixing from Shopify."""
    import requests

    store = os.getenv("SHOPIFY_STORE_DOMAIN", "the-rike-inc.myshopify.com").strip()
    if not store.startswith("http"):
        store = "https://" + store
    token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    blog_id = os.getenv("SHOPIFY_BLOG_ID")

    if not token or not blog_id:
        log("Missing SHOPIFY_ACCESS_TOKEN or SHOPIFY_BLOG_ID")
        return []

    url = f"{store}/admin/api/2025-01/blogs/{blog_id}/articles.json?limit=50&status=any"
    headers = {"X-Shopify-Access-Token": token}

    try:
        r = requests.get(url, headers=headers, timeout=30)
        articles = r.json().get("articles", [])
    except Exception as e:
        log(f"Failed to fetch articles: {e}")
        return []

    # Filter articles that might need fixing (check for common issues)
    needs_fix = []
    for a in articles:
        body = a.get("body_html", "") or ""
        title = a.get("title", "")

        # Check for issues
        issues = []

        # 1. Check for generic content patterns
        generic_patterns = [
            "Central to",
            "and used throughout the content below",
            "A clean workspace, basic tools, and reliable materials",
            "provides guidelines and best practices",
            # New generic Key Terms patterns
            "The primary concept discussed here, essential for achieving",
            "A critical element that directly impacts the quality and outcome",
            "Understanding this helps you make informed decisions during each step",
            "Mastering this technique separates beginners from experienced",
            "This foundational knowledge enables you to troubleshoot",
            "Knowing this term helps you communicate clearly with other",
            "Key concept related to this topic",
        ]
        for p in generic_patterns:
            if p.lower() in body.lower():
                issues.append("GENERIC_CONTENT")
                break

        # 2. Check for broken images
        if "Too Many Requests" in body or "pollinations.ai/prompt" in body:
            issues.append("BROKEN_IMAGES")

        # 3. Check for thin content
        word_count = len(body.split())
        if word_count < 1000:
            issues.append("THIN_CONTENT")

        if issues:
            needs_fix.append({"id": a["id"], "title": title[:50], "issues": issues})

    return needs_fix


def trigger_workflow(article_id: str, dry_run: bool = False) -> bool:
    """Trigger the Article Pre-Publish Review workflow via gh CLI."""
    cmd = [
        "gh",
        "workflow",
        "run",
        "Article Pre-Publish Review",
        "--ref",
        "feat/l6-reconcile-main",
        "-f",
        f"article_id={article_id}",
    ]

    if dry_run:
        log(f"[DRY-RUN] Would run: {' '.join(cmd)}")
        return True

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            log(f"✓ Triggered workflow for article {article_id}")
            return True
        else:
            log(f"✗ Failed to trigger workflow: {result.stderr}")
            return False
    except Exception as e:
        log(f"✗ Error triggering workflow: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run sequential article fixes with intervals"
    )
    parser.add_argument(
        "--max", type=int, default=10, help="Max articles to process (default: 10)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=900,
        help="Seconds between articles (default: 900 = 15 min, matches GHA schedule)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would run without executing"
    )
    parser.add_argument(
        "--ids", type=str, help="Comma-separated list of article IDs to process"
    )
    args = parser.parse_args()

    log(f"=== Sequential Article Fix Runner ===")
    log(
        f"Max articles: {args.max}, Interval: {args.interval}s ({args.interval//60} min)"
    )

    # Get articles to fix
    if args.ids:
        article_ids = [
            {"id": int(x.strip()), "title": "Manual", "issues": ["MANUAL"]}
            for x in args.ids.split(",")
            if x.strip()
        ]
    else:
        log("Fetching articles that need fixing...")
        article_ids = get_articles_needing_fix()

    if not article_ids:
        log("No articles found that need fixing!")
        return

    log(f"Found {len(article_ids)} articles needing fixes")

    # Limit to max
    to_process = article_ids[: args.max]
    log(f"Will process {len(to_process)} articles")
    print()

    # Process each article
    for i, article in enumerate(to_process):
        aid = article["id"]
        title = article.get("title", "Unknown")
        issues = article.get("issues", [])

        log(f"[{i+1}/{len(to_process)}] Article {aid}: {title}")
        log(f"    Issues: {issues}")

        success = trigger_workflow(str(aid), dry_run=args.dry_run)

        # Wait interval before next article (except for last one)
        if i < len(to_process) - 1 and not args.dry_run:
            log(
                f"    Waiting {args.interval}s ({args.interval//60} min) before next article..."
            )
            for remaining in range(args.interval, 0, -60):
                mins = remaining // 60
                print(f"\r    Next article in {mins} min...   ", end="", flush=True)
                time.sleep(min(60, remaining))
            print()

    log("=== Done! ===")


if __name__ == "__main__":
    main()
