#!/usr/bin/env python3
"""
Ensure article has a featured image (from first inline, prefer Shopify CDN).
Run after cleanup_before_publish, before publish. Only updates article.image if missing/invalid.
Usage: python set_featured_image_if_missing.py <article_id>
"""
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    for p in [Path(__file__).parent.parent / ".env", Path(__file__).parent / ".env"]:
        if p.exists():
            load_dotenv(p)
            break
except Exception:
    pass

def _load_publish_config():
    p = Path(__file__).parent.parent / "SHOPIFY_PUBLISH_CONFIG.json"
    if not p.exists():
        return {}
    try:
        import json
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

_cfg = _load_publish_config()
_shop = _cfg.get("shop", {})

SHOP = (os.environ.get("SHOPIFY_SHOP") or os.environ.get("SHOPIFY_STORE_DOMAIN") or "").strip()
if not SHOP:
    SHOP = (_shop.get("domain") or "").strip()
if SHOP and ".myshopify.com" not in SHOP:
    SHOP = f"{SHOP}.myshopify.com"
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID") or os.environ.get("BLOG_ID") or ""
TOKEN = (os.environ.get("SHOPIFY_ACCESS_TOKEN") or _shop.get("access_token") or "").strip()
API_VERSION = os.environ.get("SHOPIFY_API_VERSION") or _shop.get("api_version") or "2025-01"


def get_article(article_id: str):
    import requests
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    r = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"})
    if r.status_code != 200:
        return None
    return r.json().get("article")


def put_image_only(article_id: str, image_src: str) -> bool:
    import requests
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    payload = {"article": {"image": {"src": image_src}}}
    r = requests.put(url, headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}, json=payload)
    if r.status_code != 200:
        print("PUT image failed: %s %s" % (r.status_code, r.text[:300]))
        return False
    print("Featured image set OK")
    return True


def first_image_src(html: str, prefer_shopify_cdn: bool = True) -> str | None:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    imgs = soup.find_all("img", src=True)
    if not imgs:
        return None
    first_any = None
    first_cdn = None
    for img in imgs:
        src = (img.get("src") or "").strip()
        if not src:
            continue
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            src = f"https://{SHOP}" + src
        if first_any is None:
            first_any = src
        if first_cdn is None and "cdn.shopify.com" in src:
            first_cdn = src
            if prefer_shopify_cdn:
                return first_cdn
    return first_cdn if (prefer_shopify_cdn and first_cdn) else first_any


def main():
    if len(sys.argv) < 2:
        print("Usage: python set_featured_image_if_missing.py <article_id>")
        sys.exit(1)
    if not SHOP or not BLOG_ID or not TOKEN:
        print("Missing SHOPIFY_* env")
        sys.exit(1)
    article_id = sys.argv[1].strip()
    article = get_article(article_id)
    if not article:
        print("Article not found")
        sys.exit(1)
    body = article.get("body_html") or ""
    current = article.get("image") or {}
    current_src = (current.get("src") or "").strip()
    has_valid = current_src and "cdn.shopify.com" in current_src
    if has_valid:
        sys.exit(0)
    image_src = first_image_src(body, prefer_shopify_cdn=True)
    if not image_src:
        print("No inline image to use as featured")
        sys.exit(0)
    ok = put_image_only(article_id, image_src)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
