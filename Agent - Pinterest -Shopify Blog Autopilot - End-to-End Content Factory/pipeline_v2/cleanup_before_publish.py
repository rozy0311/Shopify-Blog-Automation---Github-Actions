#!/usr/bin/env python3
"""
Clean article body before publish: strip generic sections, dedupe paragraphs, ensure featured image.
Run from pipeline_v2 with SHOPIFY_* env set. Usage:
  python cleanup_before_publish.py <article_id>
"""
import os
import re
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

# Fallback: load from SHOPIFY_PUBLISH_CONFIG.json (repo root)
def _load_publish_config():
    p = Path(__file__).parent.parent / "SHOPIFY_PUBLISH_CONFIG.json"
    if not p.exists():
        return {}
    try:
        import json
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

_from_config = _load_publish_config()
_shop_cfg = _from_config.get("shop", {})

from bs4 import BeautifulSoup

SHOP = (os.environ.get("SHOPIFY_SHOP") or os.environ.get("SHOPIFY_STORE_DOMAIN") or "").strip()
if not SHOP:
    SHOP = (_shop_cfg.get("domain") or "").strip()
if SHOP and ".myshopify.com" not in SHOP:
    SHOP = f"{SHOP}.myshopify.com"
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID") or os.environ.get("BLOG_ID") or ""
TOKEN = (os.environ.get("SHOPIFY_ACCESS_TOKEN") or _shop_cfg.get("access_token") or "").strip()
API_VERSION = os.environ.get("SHOPIFY_API_VERSION") or _shop_cfg.get("api_version") or "2025-01"

# Section headings to remove (generic / template contamination)
GENERIC_HEADINGS = {
    "practical tips", "maintenance and care", "research highlights", "expert insights",
    "step-by-step approach", "key terms", "sources & further reading", "sources &amp; further reading",
    "advanced techniques for experienced practitioners", "customization and personalization",
    "batch production", "quality enhancement", "creative variations",
    "supporting data", "cited quotes", "key concept related to this topic",
}

def get_article(article_id: str):
    import requests
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    r = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"})
    if r.status_code != 200:
        print("GET article failed: %s %s" % (r.status_code, r.text[:300]))
        return None
    return r.json().get("article")

def put_article(article_id: str, body_html: str, image_src: str | None = None) -> bool:
    import requests
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    payload = {"article": {"body_html": body_html}}
    if image_src:
        payload["article"]["image"] = {"src": image_src}
    r = requests.put(url, headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}, json=payload)
    if r.status_code != 200:
        print("PUT article failed: %s %s" % (r.status_code, r.text[:400]))
        return False
    print("PUT article OK (body updated)")
    return True

def is_generic_heading(tag) -> bool:
    if tag.name not in ("h2", "h3", "h4"):
        return False
    text = tag.get_text(strip=True).lower()
    return any(gh in text for gh in GENERIC_HEADINGS)

def strip_generic_sections(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    to_remove = []
    seen = set()
    for tag in soup.find_all(["h2", "h3", "h4"]):
        if not is_generic_heading(tag):
            continue
        if id(tag) in seen:
            continue
        to_remove.append(tag)
        seen.add(id(tag))
        level = tag.name
        for sib in tag.find_next_siblings():
            if sib.name and sib.name in ("h2", "h3", "h4"):
                if sib.name <= level:
                    break
            if id(sib) not in seen:
                to_remove.append(sib)
                seen.add(id(sib))
    for tag in to_remove:
        try:
            tag.decompose()
        except Exception:
            pass
    return str(soup)

def dedupe_paragraphs(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    to_remove = []
    for p in soup.find_all("p"):
        text = re.sub(r"\s+", " ", p.get_text(strip=True))
        if len(text) < 20:
            continue
        key = text[:200]
        if key in seen:
            to_remove.append(p)
        else:
            seen.add(key)
    for p in to_remove:
        try:
            p.decompose()
        except Exception:
            pass
    return str(soup)

def first_image_src(html: str, prefer_shopify_cdn: bool = True) -> str | None:
    """First <img> src in body. If prefer_shopify_cdn, return first cdn.shopify.com src if any."""
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
        print("Usage: python cleanup_before_publish.py <article_id>")
        sys.exit(1)
    if not SHOP or not BLOG_ID or not TOKEN:
        print("Missing SHOPIFY_SHOP, SHOPIFY_BLOG_ID, or SHOPIFY_ACCESS_TOKEN")
        sys.exit(1)
    article_id = sys.argv[1].strip()
    article = get_article(article_id)
    if not article:
        sys.exit(1)
    body = article.get("body_html") or ""
    if not body:
        print("Article has no body_html")
        sys.exit(0)
    body = strip_generic_sections(body)
    body = dedupe_paragraphs(body)
    current_image = article.get("image") or {}
    current_src = (current_image.get("src") or "").strip()
    has_valid_featured = current_src and "cdn.shopify.com" in current_src
    image_src = None
    if not has_valid_featured:
        image_src = first_image_src(body, prefer_shopify_cdn=True)
        if image_src:
            print("Setting featured image from first inline image (prefer Shopify CDN)")
        else:
            print("WARN: No inline image found; article may have no featured image")
    ok = put_article(article_id, body, image_src)
    if ok and image_src:
        print("Featured image sent to Shopify (check Admin if not visible)")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
