#!/usr/bin/env python3
"""
Fix already-published articles that contain generic AI phrases.

- Fetches each article, strips GENERIC_PHRASES and generic section headings from body_html.
- Updates the article via API (article stays published; only body_html is replaced).
- Use for blogs already live that slipped through with generic content.

Usage:
  python fix_published_generic.py --dry-run              # Show what would change, no writes
  python fix_published_generic.py --all                  # Fix all published articles
  python fix_published_generic.py --file ids.txt        # Fix IDs listed in file (one per line)
  python fix_published_generic.py 123 456 789           # Fix these article IDs

Requires: SHOPIFY_SHOP, SHOPIFY_ACCESS_TOKEN, SHOPIFY_BLOG_ID (or SHOPIFY_PUBLISH_CONFIG.json).
"""

import argparse
import os
import sys
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).parent.parent
ENV_PATHS = [ROOT_DIR / ".env", ROOT_DIR.parent / ".env"]


def load_env(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key, value)


def get_shopify_env() -> dict[str, str]:
    shop = os.environ.get("SHOPIFY_SHOP") or os.environ.get("SHOPIFY_STORE_DOMAIN")
    token = os.environ.get("SHOPIFY_ACCESS_TOKEN")
    blog_id = os.environ.get("SHOPIFY_BLOG_ID") or os.environ.get("BLOG_ID")
    api_version = os.environ.get("SHOPIFY_API_VERSION") or "2025-01"
    config_path = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"
    if config_path.exists():
        try:
            import json
            config = json.loads(config_path.read_text(encoding="utf-8"))
            shop = shop or config.get("shop", {}).get("domain", "")
            token = token or config.get("shop", {}).get("access_token", "")
            blog_id = blog_id or config.get("shop", {}).get("blog_id", "")
        except Exception:
            pass
    return {
        "shop": shop or "",
        "token": token or "",
        "blog_id": blog_id or "",
        "api_version": api_version,
    }


def fetch_article(article_id: int, env: dict[str, str]) -> dict | None:
    if not env["shop"] or not env["token"] or not env["blog_id"]:
        return None
    url = f"https://{env['shop']}/admin/api/{env['api_version']}/blogs/{env['blog_id']}/articles/{article_id}.json"
    headers = {"X-Shopify-Access-Token": env["token"]}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code != 200:
        return None
    return resp.json().get("article")


def update_article_body(article_id: int, body_html: str, env: dict[str, str]) -> bool:
    if not env["shop"] or not env["token"] or not env["blog_id"]:
        return False
    url = f"https://{env['shop']}/admin/api/{env['api_version']}/blogs/{env['blog_id']}/articles/{article_id}.json"
    headers = {
        "X-Shopify-Access-Token": env["token"],
        "Content-Type": "application/json",
    }
    payload = {"article": {"id": article_id, "body_html": body_html}}
    resp = requests.put(url, headers=headers, json=payload, timeout=30)
    return resp.status_code == 200


def list_published_article_ids(env: dict[str, str], limit: int = 250) -> list[int]:
    if not env["shop"] or not env["token"] or not env["blog_id"]:
        return []
    url = (
        f"https://{env['shop']}/admin/api/{env['api_version']}/blogs/{env['blog_id']}/articles.json"
        f"?limit={limit}&status=published"
    )
    headers = {"X-Shopify-Access-Token": env["token"]}
    ids: list[int] = []
    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            break
        data = resp.json()
        for a in data.get("articles", []):
            aid = a.get("id")
            if aid:
                ids.append(aid)
        url = None
        link = resp.headers.get("Link")
        if link and "next" in link:
            for part in link.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip(" <>")
                    break
    return ids


def main() -> int:
    load_env(ENV_PATHS)
    parser = argparse.ArgumentParser(
        description="Strip generic phrases from already-published articles."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be updated; do not send PUT.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all published articles on the blog.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        metavar="PATH",
        help="Read article IDs from file (one per line).",
    )
    parser.add_argument(
        "ids",
        nargs="*",
        type=int,
        help="Article IDs to fix.",
    )
    args = parser.parse_args()

    env = get_shopify_env()
    if not env["shop"] or not env["token"] or not env["blog_id"]:
        print("Missing SHOPIFY_SHOP, SHOPIFY_ACCESS_TOKEN, or SHOPIFY_BLOG_ID.", file=sys.stderr)
        return 1

    # Resolve list of IDs
    ids: list[int] = []
    if args.all:
        ids = list_published_article_ids(env)
        if not ids:
            print("No published articles found.")
            return 0
        print(f"Found {len(ids)} published article(s).")
    elif args.file and args.file.exists():
        ids = [int(line.strip()) for line in args.file.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        ids = args.ids or []

    if not ids:
        print("No article IDs to process. Use --all, --file <path>, or pass IDs.")
        return 1

    # Import strip logic (same as run_meta_fix_queue / pre_publish_review)
    try:
        from run_meta_fix_queue import strip_generic_phrases
    except Exception:
        print("run_meta_fix_queue not available; cannot strip generic phrases.", file=sys.stderr)
        return 1

    updated = 0
    skipped = 0
    errors = 0
    for aid in ids:
        article = fetch_article(aid, env)
        if not article:
            print(f"  [{aid}] fetch failed")
            errors += 1
            continue
        body = article.get("body_html", "") or ""
        cleaned = strip_generic_phrases(body)
        if cleaned == body:
            skipped += 1
            continue
        if args.dry_run:
            print(f"  [{aid}] would update (body length {len(body)} -> {len(cleaned)})")
            updated += 1
            continue
        if update_article_body(aid, cleaned, env):
            print(f"  [{aid}] updated")
            updated += 1
        else:
            print(f"  [{aid}] update failed")
            errors += 1

    print(f"\nDone: {updated} updated, {skipped} unchanged, {errors} errors.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
