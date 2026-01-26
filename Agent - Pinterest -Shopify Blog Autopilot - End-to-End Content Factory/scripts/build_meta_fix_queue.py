#!/usr/bin/env python3
"""
Build a one-item meta_fix_queue.json for a specific article.
This is used to run content meta-prompt fixes sequentially (no batch).
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).parent.parent
CONTENT_DIR = ROOT_DIR / "content"
QUEUE_PATH = CONTENT_DIR / "meta_fix_queue.json"


def get_shopify_env() -> dict[str, str]:
    shop = os.environ.get("SHOPIFY_SHOP") or os.environ.get("SHOPIFY_STORE_DOMAIN")
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get("SHOPIFY_TOKEN")
    blog_id = os.environ.get("SHOPIFY_BLOG_ID") or os.environ.get("BLOG_ID")
    api_version = os.environ.get("SHOPIFY_API_VERSION") or "2025-01"
    return {
        "shop": shop or "",
        "token": token or "",
        "blog_id": blog_id or "",
        "api_version": api_version,
    }


def fetch_article(article_id: int, env: dict[str, str]) -> dict[str, str] | None:
    if not env["shop"] or not env["token"] or not env["blog_id"]:
        return None
    url = f"https://{env['shop']}/admin/api/{env['api_version']}/blogs/{env['blog_id']}/articles/{article_id}.json"
    headers = {"X-Shopify-Access-Token": env["token"]}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        return None
    return resp.json().get("article")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: build_meta_fix_queue.py <article_id>")
        return 1

    article_id = int(sys.argv[1])
    env = get_shopify_env()
    article = fetch_article(article_id, env)
    if not article:
        print("Failed to fetch article for meta fix queue.")
        return 1

    now = datetime.now().isoformat()
    item = {
        "article_id": str(article_id),
        "title": article.get("title", ""),
        "url": article.get("handle", ""),
        "score": 0,
        "status": "pending",
        "attempts": 0,
        "last_error": "",
        "created_at": now,
        "updated_at": now,
        "missing": [
            {"severity": "CRITICAL", "category": "Citations", "message": "Missing citations"},
            {"severity": "CRITICAL", "category": "Statistics", "message": "Missing statistics"},
            {"severity": "CRITICAL", "category": "Expert Quotes", "message": "Missing expert quotes"},
            {"severity": "CRITICAL", "category": "Word Count", "message": "Below target word count"},
        ],
    }

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps([item], ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Meta fix queue created for article {article_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
