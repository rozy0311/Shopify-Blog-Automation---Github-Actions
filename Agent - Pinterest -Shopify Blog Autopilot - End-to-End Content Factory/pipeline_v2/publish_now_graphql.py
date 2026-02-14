"""
Publish one article so it shows on storefront: set published_at to NOW (UTC) via REST + GraphQL.
Run from repo root with .env loaded. Usage:
  python pipeline_v2/publish_now_graphql.py <article_id>
  python pipeline_v2/publish_now_graphql.py 691791954238
"""
import os
import sys
from datetime import datetime, timezone

# Load env from repo root
try:
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).parent.parent / ".env")
except Exception:
    pass

def _load_publish_config():
    from pathlib import Path
    p = Path(__file__).parent.parent / "SHOPIFY_PUBLISH_CONFIG.json"
    if not p.exists():
        return {}
    try:
        import json
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

_cfg = _load_publish_config()
_shop_cfg = _cfg.get("shop", {})
_defaults = _cfg.get("defaults", {})

SHOP = (os.environ.get("SHOPIFY_SHOP") or os.environ.get("SHOPIFY_STORE_DOMAIN") or "").strip()
if not SHOP:
    SHOP = (os.environ.get("SHOPIFY_STORE") or _shop_cfg.get("domain") or "").strip()
if SHOP and ".myshopify.com" not in SHOP:
    SHOP = f"{SHOP}.myshopify.com"
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID") or os.environ.get("BLOG_ID") or ""
TOKEN = (os.environ.get("SHOPIFY_ACCESS_TOKEN") or _shop_cfg.get("access_token") or "").strip()
API_VERSION = os.environ.get("SHOPIFY_API_VERSION") or _shop_cfg.get("api_version") or "2025-01"
BLOG_HANDLE = os.environ.get("SHOPIFY_BLOG_HANDLE") or _defaults.get("blog_handle") or "sustainable-living"
JSON_CT = "application/json"

if not SHOP or not BLOG_ID or not TOKEN:
    print("Missing SHOPIFY_SHOP/SHOPIFY_STORE, SHOPIFY_BLOG_ID, or SHOPIFY_ACCESS_TOKEN in .env")
    sys.exit(1)

def get_article(article_id: str):
    import requests
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    r = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": JSON_CT})
    if r.status_code != 200:
        print("GET article failed: %s %s" % (r.status_code, r.text[:300]))
        return None
    return r.json().get("article")

def update_rest(article_id: str, published_at: str) -> bool:
    import requests
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    payload = {
        "article": {
            "published": True,
            "published_at": published_at,
        }
    }
    r = requests.put(url, headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": JSON_CT}, json=payload)
    if r.status_code != 200:
        print("REST update failed: %s %s" % (r.status_code, r.text[:400]))
        return False
    print("[OK] REST: published_at=%s" % published_at)
    return True

def update_graphql(article_id: str, is_published: bool, publish_date: str) -> bool:
    import requests
    gql_url = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"
    gid = f"gid://shopify/Article/{article_id}"
    query = """
    mutation articleUpdate($id: ID!, $article: ArticleUpdateInput!) {
      articleUpdate(id: $id, article: $article) {
        article { id }
        userErrors { field, message }
      }
    }
    """
    variables = {
        "id": gid,
        "article": {
            "isPublished": is_published,
            "publishDate": publish_date,
        },
    }
    r = requests.post(gql_url, headers={"X-Shopify-Access-Token": TOKEN, "Content-Type": JSON_CT}, json={"query": query, "variables": variables})
    data = r.json() if r.ok else {}
    errs = (data.get("data") or {}).get("articleUpdate") or {}
    user_errors = errs.get("userErrors") or []
    if user_errors:
        for e in user_errors:
            print("[WARN] GraphQL: %s" % e.get("message", str(e)))
        return False
    if not r.ok:
        print("GraphQL request failed: %s %s" % (r.status_code, r.text[:300]))
        return False
    print("[OK] GraphQL: isPublished=true, publishDate=%s (storefront)" % publish_date)
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python pipeline_v2/publish_now_graphql.py <article_id>")
        sys.exit(1)
    article_id = sys.argv[1].strip()
    published_at_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    article = get_article(article_id)
    if not article:
        print("Article not found. Check BLOG_ID=%s and article id." % BLOG_ID)
        sys.exit(1)

    existing_pub = article.get("published_at")
    print("Article: id=%s title=%s published_at=%s handle=%s" % (
        article.get("id"), (article.get("title") or "")[:50], existing_pub, article.get("handle")
    ))

    # If already published, preserve original date to avoid bumping to top of feed
    if existing_pub:
        print("[SKIP] Article already published at %s — keeping original date (no re-publish)." % existing_pub)
        sys.exit(0)

    rest_ok = update_rest(article_id, published_at_now)
    gql_ok = update_graphql(article_id, True, published_at_now)
    if not rest_ok and not gql_ok:
        print("[WARN] Both REST and GraphQL failed.")
        sys.exit(1)

    # Refetch and print URL
    article = get_article(article_id)
    if article:
        h = article.get("handle") or ""
        print("published_at now: %s" % article.get("published_at"))
        if h:
            print("Storefront URL: https://%s/blogs/%s/%s" % (SHOP, BLOG_HANDLE, h))
    print("Done. If still not visible: check Shopify Admin > Online Store > Blog > article status and sales channel.")

if __name__ == "__main__":
    main()
