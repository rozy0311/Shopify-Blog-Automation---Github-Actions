#!/usr/bin/env python3
"""
Update Shopify articles' featured images from a backup JSON.

Reads a backup from backup_featured_images.py (e.g. 20260203T090432Z_featured_images.json).
For each article that has image.src in the backup, PUTs that image to the Shopify article.

Usage:
  python update_shopify_featured_from_backup.py
    # uses latest file in backups_featured_images/
  python update_shopify_featured_from_backup.py --file "path/to/20260203T090432Z_featured_images.json"
  python update_shopify_featured_from_backup.py --dry-run
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    for p in [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent / ".env",
    ]:
        if p.exists():
            load_dotenv(p)
            break
except ImportError:
    pass

import requests

PIPELINE_DIR = Path(__file__).parent
BACKUP_DIR = PIPELINE_DIR / "backups_featured_images"

SHOP = os.environ.get("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "108441862462")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get("SHOPIFY_TOKEN")
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

if not TOKEN:
    raise SystemExit("Missing SHOPIFY_ACCESS_TOKEN")

HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}


def latest_backup_path() -> Path | None:
    """Return path to most recent *_featured_images.json in BACKUP_DIR."""
    if not BACKUP_DIR.exists():
        return None
    files = list(BACKUP_DIR.glob("*_featured_images.json"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def load_backup(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def put_article_image(article_id: str, image_src: str, image_alt: str) -> bool:
    """Set article featured image via PUT. Returns True on success."""
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    payload = {
        "article": {
            "id": int(article_id),
            "image": {"src": image_src, "alt": image_alt or ""},
        }
    }
    resp = requests.put(url, headers=HEADERS, json=payload, timeout=30)
    if resp.status_code not in (200, 201):
        print(f"  [FAIL] {article_id}: HTTP {resp.status_code} {resp.text[:150]}")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Shopify featured images from backup")
    parser.add_argument("--file", "-f", type=str, help="Path to backup JSON (default: latest in backups_featured_images)")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be updated")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between PUTs (default 0.5)")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.is_absolute():
            path = PIPELINE_DIR / path
    else:
        path = latest_backup_path()
        if not path:
            print("No backup file found. Run backup_featured_images.py first or pass --file.")
            return 1

    if not path.exists():
        print(f"File not found: {path}")
        return 1

    print(f"Loading backup: {path}")
    data = load_backup(path)
    articles = data.get("articles") or []
    to_update = [
        a for a in articles
        if a.get("image") and (a["image"].get("src") or "").strip()
    ]
    print(f"Backup has {len(articles)} articles, {len(to_update)} with featured image to update on Shopify.")

    if args.dry_run:
        for a in to_update[:10]:
            print(f"  Would set: {a['article_id']} {a.get('title', '')[:50]} -> {a['image']['src'][:60]}...")
        if len(to_update) > 10:
            print(f"  ... and {len(to_update) - 10} more.")
        return 0

    ok, fail = 0, 0
    for i, a in enumerate(to_update, 1):
        aid = a["article_id"]
        src = a["image"]["src"].strip()
        alt = (a["image"].get("alt") or "").strip()
        if put_article_image(aid, src, alt):
            ok += 1
        else:
            fail += 1
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(to_update)}")
        time.sleep(args.delay)

    print(f"\nDone. Updated: {ok}, Failed: {fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
