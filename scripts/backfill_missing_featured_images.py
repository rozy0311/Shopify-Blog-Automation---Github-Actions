#!/usr/bin/env python3
import base64
import hashlib
import os
import sys
from typing import Any

import requests


def env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


SHOP = env("SHOPIFY_SHOP") or env("SHOPIFY_STORE_DOMAIN")
if SHOP and ".myshopify.com" not in SHOP:
    SHOP = f"{SHOP}.myshopify.com"

TOKEN = env("SHOPIFY_ACCESS_TOKEN") or env("SHOPIFY_TOKEN")
BLOG_ID = env("SHOPIFY_BLOG_ID") or env("BLOG_ID")
BLOG_HANDLE = env("BLOG_HANDLE")
API_VERSION = env("SHOPIFY_API_VERSION", "2025-01")
LIMIT = int(env("BACKFILL_LIMIT", "100"))
DRY_RUN = env("BACKFILL_DRY_RUN", "false").lower() == "true"


def headers() -> dict[str, str]:
    return {
        "X-Shopify-Access-Token": TOKEN,
        "Content-Type": "application/json",
    }


def ensure_env() -> None:
    missing = [name for name, value in {
        "SHOPIFY_SHOP": SHOP,
        "SHOPIFY_ACCESS_TOKEN": TOKEN,
    }.items() if not value]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")


def resolve_blog_id() -> str:
    if BLOG_ID:
        return BLOG_ID
    if not BLOG_HANDLE:
        raise RuntimeError("Missing SHOPIFY_BLOG_ID and BLOG_HANDLE")

    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs.json"
    response = requests.get(url, headers=headers(), timeout=30)
    response.raise_for_status()
    blogs = response.json().get("blogs", [])
    for blog in blogs:
        if (blog.get("handle") or "").strip() == BLOG_HANDLE:
            return str(blog.get("id"))

    raise RuntimeError(f"Cannot resolve blog id for handle: {BLOG_HANDLE}")


def list_published_articles(limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    next_page_info: str | None = None
    page_size = min(250, max(1, limit))

    while len(results) < limit:
        base = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{RESOLVED_BLOG_ID}/articles.json"
        params: dict[str, Any] = {
            "status": "published",
            "limit": min(page_size, limit - len(results)),
            "fields": "id,title,image,published_at,updated_at",
        }
        if next_page_info:
            params = {
                "limit": min(page_size, limit - len(results)),
                "page_info": next_page_info,
                "fields": "id,title,image,published_at,updated_at",
            }

        response = requests.get(base, headers=headers(), params=params, timeout=30)
        response.raise_for_status()
        batch = response.json().get("articles", [])
        if not batch:
            break
        results.extend(batch)

        link = response.headers.get("Link", "")
        next_page_info = parse_next_page_info(link)
        if not next_page_info:
            break

    return results[:limit]


def parse_next_page_info(link_header: str) -> str | None:
    if 'rel="next"' not in link_header:
        return None
    parts = link_header.split(",")
    for part in parts:
        if 'rel="next"' not in part:
            continue
        marker = "page_info="
        idx = part.find(marker)
        if idx < 0:
            continue
        tail = part[idx + len(marker):]
        end = tail.find("&")
        value = tail if end < 0 else tail[:end]
        value = value.split(">", 1)[0].strip()
        if value:
            return value
    return None


def has_featured_image(article: dict[str, Any]) -> bool:
    image = article.get("image") or {}
    src = (image.get("src") or "").strip()
    return bool(src)


def fallback_image_url(seed_text: str) -> str:
    digest = hashlib.sha1(seed_text.encode("utf-8")).hexdigest()[:12]
    return f"https://picsum.photos/seed/{digest}/1536/1024"


def fetch_image_attachment(url: str) -> str | None:
    resp = requests.get(url, timeout=30, allow_redirects=True)
    if resp.status_code != 200:
        return None
    content_type = (resp.headers.get("Content-Type") or "").lower()
    if "image/" not in content_type:
        return None
    if not resp.content:
        return None
    if len(resp.content) > 12 * 1024 * 1024:
        return None
    return base64.b64encode(resp.content).decode("ascii")


def update_featured_image(article_id: int, title: str, attachment: str) -> bool:
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{RESOLVED_BLOG_ID}/articles/{article_id}.json"
    payload = {
        "article": {
            "id": article_id,
            "image": {
                "attachment": attachment,
                "alt": title[:255],
            },
        }
    }
    response = requests.put(url, headers=headers(), json=payload, timeout=30)
    if response.status_code != 200:
        print(f"[WARN] update failed article={article_id} status={response.status_code} body={response.text[:300]}")
        return False
    return True


def main() -> int:
    ensure_env()
    print(f"[INFO] shop={SHOP} blog_id={RESOLVED_BLOG_ID} api={API_VERSION} limit={LIMIT} dry_run={DRY_RUN}")

    published = list_published_articles(LIMIT)
    print(f"[INFO] fetched published articles: {len(published)}")

    missing = [a for a in published if not has_featured_image(a)]
    print(f"[INFO] missing featured image: {len(missing)}")

    updated = 0
    failed = 0

    for article in missing:
        article_id = int(article["id"])
        title = (article.get("title") or f"Article {article_id}").strip()
        url = fallback_image_url(f"{article_id}:{title}")
        attachment = fetch_image_attachment(url)
        if not attachment:
            print(f"[WARN] cannot fetch fallback image for article={article_id}")
            failed += 1
            continue

        if DRY_RUN:
            print(f"[DRY] would set featured image for article={article_id} title={title}")
            updated += 1
            continue

        if update_featured_image(article_id, title, attachment):
            print(f"[OK] set featured image article={article_id} title={title}")
            updated += 1
        else:
            failed += 1

    print(f"[SUMMARY] scanned={len(published)} missing={len(missing)} updated={updated} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    try:
        RESOLVED_BLOG_ID = resolve_blog_id()
        sys.exit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)
