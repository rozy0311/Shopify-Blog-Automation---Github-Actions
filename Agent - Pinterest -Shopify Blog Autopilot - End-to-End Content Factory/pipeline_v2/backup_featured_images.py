#!/usr/bin/env python3
"""
Backup featured images of blogs that have passed meta prompt.

Reads content/meta_fix_queue.json: "passed" = status=="done" and no CRITICAL in missing.
For each passed article, fetches current article from Shopify and saves featured image (src, alt).
Output: pipeline_v2/backups_featured_images/<timestamp>_featured_images.json

Usage:
  python backup_featured_images.py                    # from meta_fix_queue (passed only)
  python backup_featured_images.py --all             # all articles in blog
  python backup_featured_images.py --ids 123,456      # specific article IDs
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Load .env from project
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
CONTENT_DIR = PIPELINE_DIR.parent
META_FIX_QUEUE = CONTENT_DIR / "content" / "meta_fix_queue.json"
BACKUP_DIR = PIPELINE_DIR / "backups_featured_images"

SHOP = os.environ.get("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "108441862462")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get("SHOPIFY_TOKEN")
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

if not TOKEN:
    raise SystemExit("Missing SHOPIFY_ACCESS_TOKEN")

HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}


def load_meta_fix_queue() -> list:
    """Load content/meta_fix_queue.json."""
    if not META_FIX_QUEUE.exists():
        print(f"[WARN] {META_FIX_QUEUE} not found; returning empty list.")
        return []
    with open(META_FIX_QUEUE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def passed_meta_prompt(entry: dict) -> bool:
    """True if entry has status done and no CRITICAL in missing."""
    if entry.get("status") != "done":
        return False
    missing = entry.get("missing") or []
    for m in missing:
        if (m or {}).get("severity") == "CRITICAL":
            return False
    return True


def get_passed_article_ids() -> list[tuple[str, str]]:
    """Return [(article_id, title), ...] for entries that passed meta prompt."""
    queue = load_meta_fix_queue()
    out = []
    for entry in queue:
        if not passed_meta_prompt(entry):
            continue
        aid = entry.get("article_id")
        if not aid:
            continue
        out.append((str(aid).strip(), (entry.get("title") or "").strip()))
    return out


def get_article(article_id: str) -> dict | None:
    """Fetch single article from Shopify (includes image)."""
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        print(f"  [WARN] GET {article_id}: HTTP {resp.status_code}")
        return None
    return resp.json().get("article")


def get_all_article_ids_from_blog(limit: int = 250) -> list[str]:
    """Fetch article IDs from blog (paginated)."""
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles.json"
    params = {"limit": min(250, limit), "fields": "id,title"}
    ids = []
    while True:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"[WARN] GET articles: HTTP {resp.status_code}")
            break
        data = resp.json()
        articles = data.get("articles") or []
        for a in articles:
            ids.append(str(a["id"]))
        if len(articles) < (params.get("limit") or 250):
            break
        params["since_id"] = articles[-1]["id"]
    return ids


def backup_featured(article_ids_with_titles: list[tuple[str, str]]) -> list[dict]:
    """For each (id, title), fetch article and collect featured image. Returns list of records."""
    records = []
    for i, (article_id, title_from_queue) in enumerate(article_ids_with_titles, 1):
        print(f"  [{i}/{len(article_ids_with_titles)}] {article_id} {title_from_queue[:50] or '(no title)'}...")
        article = get_article(article_id)
        if not article:
            continue
        img = article.get("image") or {}
        src = (img.get("src") or "").strip()
        alt = (img.get("alt") or "").strip()
        records.append({
            "article_id": article_id,
            "title": article.get("title") or title_from_queue,
            "handle": (article.get("handle") or "").strip(),
            "image": {"src": src, "alt": alt} if src else None,
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup featured images (passed meta or by IDs/all)")
    parser.add_argument("--ids", type=str, help="Comma-separated article IDs")
    parser.add_argument("--all", action="store_true", help="Backup all articles in blog")
    parser.add_argument("--out", type=str, help="Output JSON path (default: backups_featured_images/<ts>_featured_images.json)")
    args = parser.parse_args()

    article_ids_with_titles: list[tuple[str, str]] = []

    if args.ids:
        for aid in args.ids.split(","):
            aid = aid.strip()
            if aid:
                article_ids_with_titles.append((aid, ""))
        print(f"Backing up featured images for {len(article_ids_with_titles)} IDs from --ids")
    elif args.all:
        ids = get_all_article_ids_from_blog()
        article_ids_with_titles = [(aid, "") for aid in ids]
        print(f"Backing up featured images for {len(article_ids_with_titles)} articles (all blog)")
    else:
        article_ids_with_titles = get_passed_article_ids()
        print(f"Backing up featured images for {len(article_ids_with_titles)} articles that passed meta prompt (from meta_fix_queue)")

    if not article_ids_with_titles:
        print("No articles to backup. Exiting.")
        return 0

    records = backup_featured(article_ids_with_titles)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    default_path = BACKUP_DIR / f"{ts}_featured_images.json"
    out_path = Path(args.out) if args.out else default_path
    if not out_path.is_absolute():
        out_path = PIPELINE_DIR / out_path

    if args.ids:
        source = "ids"
    elif args.all:
        source = "all_blog"
    else:
        source = "meta_fix_queue_passed"
    payload = {
        "created_at": ts,
        "source": source,
        "count": len(records),
        "articles": records,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with_featured = sum(1 for r in records if r.get("image") and r["image"].get("src"))
    print(f"\nDone. Saved {len(records)} articles ({with_featured} with featured image) to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
