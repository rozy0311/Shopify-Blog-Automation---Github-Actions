#!/usr/bin/env python3
"""
Clean up stale queue entries and re-validate article states.
This script:
1. Fetches current state of all pending/failed articles from Shopify
2. Marks articles as 'done' if they pass quality checks
3. Clears articles with attempts >= MAX_ATTEMPTS

Usage: python cleanup_stale_queue.py [--dry-run] [--max-attempts 3]
"""

import os
import sys
import json
import argparse
import re
import requests
from pathlib import Path
from datetime import datetime

# Load env
for p in [Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
    if p.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(p)
            break
        except ImportError:
            pass

# Config
SHOP = os.getenv("SHOPIFY_STORE_DOMAIN", "the-rike-inc.myshopify.com").strip()
if not SHOP.startswith("http") and not SHOP.startswith("https"):
    SHOP = SHOP
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-01")
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

QUEUE_PATH = Path(__file__).parent / "anti_drift_queue.json"


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def get_article(article_id: str) -> dict:
    """Fetch single article from Shopify."""
    url = f"https://{SHOP}/admin/api/{API_VERSION}/articles/{article_id}.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("article")
    except Exception as e:
        log(f"Error fetching {article_id}: {e}")
    return None


def check_article_quality(article: dict) -> tuple:
    """
    Quick quality check for an article.
    Returns (is_ok, issues_list)
    """
    body = article.get("body_html", "") or ""
    title = article.get("title", "")
    issues = []

    # Check word count
    word_count = len(body.split())
    if word_count < 1000:
        issues.append(f"THIN_CONTENT ({word_count} words)")

    # Check images
    img_pattern = r'<img[^>]+src="([^"]+)"'
    images = re.findall(img_pattern, body)
    valid_images = [img for img in images if "shopify.com" in img or "cdn." in img]
    if len(valid_images) < 3:
        issues.append(f"LOW_IMAGES ({len(valid_images)}/3)")

    # Check for broken image indicators
    if "Too Many Requests" in body:
        issues.append("BROKEN_IMAGE_TEXT")
    if "pollinations.ai/prompt" in body:
        issues.append("RAW_POLLINATIONS_URL")

    # Check for generic content patterns (simplified)
    generic_patterns = [
        "Central to",
        "The primary concept discussed here",
        "A critical element that directly impacts",
        "and used throughout the content below",
    ]
    for p in generic_patterns:
        if p.lower() in body.lower():
            issues.append("GENERIC_CONTENT")
            break

    # Check featured image
    if not article.get("image"):
        issues.append("NO_FEATURED_IMAGE")

    return len(issues) == 0, issues


def cleanup_queue(max_attempts: int = 3, dry_run: bool = False):
    """Clean up stale queue entries."""
    if not QUEUE_PATH.exists():
        log("Queue file not found!")
        return

    with open(QUEUE_PATH, "r", encoding="utf-8") as f:
        queue_data = json.load(f)

    items = queue_data.get("items", [])
    log(f"Queue has {len(items)} items total")

    stats = {
        "checked": 0,
        "marked_done": 0,
        "cleared_max_attempts": 0,
        "still_pending": 0,
        "not_found": 0,
    }

    # Filter items that need checking (pending, failed, retrying)
    to_check = [
        item
        for item in items
        if item.get("status") in ("pending", "failed", "retrying")
    ]
    log(f"Checking {len(to_check)} pending/failed items...")

    for item in to_check[:50]:  # Limit to 50 to avoid timeout
        article_id = item.get("id")
        title = item.get("title", "")[:40]
        attempts = item.get("attempts", 0)
        status = item.get("status")

        stats["checked"] += 1

        # Clear items with too many attempts
        if attempts >= max_attempts and status == "failed":
            log(f"🗑️  Clearing {article_id} ({title}): {attempts} attempts exceeded")
            if not dry_run:
                item["status"] = "skipped"
                item["notes"] = f"Cleared after {attempts} failed attempts"
            stats["cleared_max_attempts"] += 1
            continue

        # Fetch and validate actual state
        article = get_article(str(article_id))
        if not article:
            log(f"❓ {article_id} ({title}): Not found in Shopify")
            if not dry_run:
                item["status"] = "skipped"
                item["notes"] = "Article not found in Shopify"
            stats["not_found"] += 1
            continue

        is_ok, issues = check_article_quality(article)

        if is_ok:
            log(f"✅ {article_id} ({title}): Passes quality - marking done")
            if not dry_run:
                item["status"] = "done"
                item["notes"] = "Validated by cleanup script"
            stats["marked_done"] += 1
        else:
            log(f"❌ {article_id} ({title}): {', '.join(issues)}")
            stats["still_pending"] += 1

    # Save updated queue
    if not dry_run:
        with open(QUEUE_PATH, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False)
        log(f"Queue saved to {QUEUE_PATH}")

    # Summary
    log("\n=== CLEANUP SUMMARY ===")
    log(f"Checked: {stats['checked']}")
    log(f"Marked done (already OK): {stats['marked_done']}")
    log(f"Cleared (max attempts): {stats['cleared_max_attempts']}")
    log(f"Not found in Shopify: {stats['not_found']}")
    log(f"Still pending: {stats['still_pending']}")

    if dry_run:
        log("\n⚠️ DRY RUN - no changes saved")


def main():
    parser = argparse.ArgumentParser(description="Clean up stale queue entries")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes")
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Max attempts before clearing (default: 3)",
    )
    args = parser.parse_args()

    log("=== QUEUE CLEANUP ===")
    cleanup_queue(max_attempts=args.max_attempts, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
