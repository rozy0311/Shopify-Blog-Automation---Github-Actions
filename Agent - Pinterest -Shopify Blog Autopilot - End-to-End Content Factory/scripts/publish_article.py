#!/usr/bin/env python3
"""
publish_article.py - Publish article to Shopify via Admin GraphQL API.

Only publishes if validator_pass AND reviewer_pass are both true.
Supports idempotency via fingerprint metafield check.

Usage:
    python scripts/publish_article.py content/article_payload.json

Environment Variables:
    SHOPIFY_STORE_DOMAIN - e.g. your-store.myshopify.com
    SHOPIFY_ADMIN_ACCESS_TOKEN - Admin API access token
    SHOPIFY_API_VERSION - e.g. 2025-10 (optional, defaults to config)
"""

import json
import os
import sys
import time
import hashlib
import requests
from pathlib import Path

# Load config
CONFIG_PATH = Path(__file__).parent.parent / "SHOPIFY_PUBLISH_CONFIG.json"
CONTENT_DIR = Path(__file__).parent.parent / "content"


def load_config():
    """Load configuration from SHOPIFY_PUBLISH_CONFIG.json"""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def get_env_with_fallback(key: str, fallback: str = None) -> str:
    """Get environment variable with optional fallback."""
    return os.environ.get(key, fallback)


def gql(
    shop_domain: str, token: str, api_version: str, query: str, variables: dict = None
):
    """Execute GraphQL query against Shopify Admin API."""
    url = f"https://{shop_domain}/admin/api/{api_version}/graphql.json"

    headers = {"Content-Type": "application/json", "X-Shopify-Access-Token": token}

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    # Retry logic with exponential backoff
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 5))
                print(f"Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                raise RuntimeError(f"GraphQL errors: {data['errors']}")

            return data.get("data", {})

        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait = (2**attempt) + 1
                print(f"Request failed, retrying in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError("Max retries exceeded")


def get_blog_id_by_handle(shop: str, token: str, api_version: str, handle: str) -> str:
    """Lookup blog ID by handle."""
    query = """
    query BlogList {
      blogs(first: 50) {
        nodes {
          id
          handle
          title
        }
      }
    }
    """

    data = gql(shop, token, api_version, query)
    blogs = data.get("blogs", {}).get("nodes", [])

    for blog in blogs:
        if blog.get("handle") == handle:
            return blog["id"]

    raise RuntimeError(f"Blog handle not found: {handle}")


def check_duplicate_by_fingerprint(
    shop: str,
    token: str,
    api_version: str,
    blog_id: str,
    fingerprint: str,
    namespace: str,
    key: str,
) -> dict:
    """Check if article with same fingerprint already exists."""
    # Query articles with the fingerprint metafield
    query = """
    query FindDuplicate($blogId: ID!) {
      blog(id: $blogId) {
        articles(first: 50) {
          nodes {
            id
            handle
            title
            metafield(namespace: "%s", key: "%s") {
              value
            }
          }
        }
      }
    }
    """ % (
        namespace,
        key,
    )

    data = gql(shop, token, api_version, query, {"blogId": blog_id})
    articles = data.get("blog", {}).get("articles", {}).get("nodes", [])

    for article in articles:
        mf = article.get("metafield")
        if mf and mf.get("value") == fingerprint:
            return article

    return None


def create_article(
    shop: str,
    token: str,
    api_version: str,
    blog_id: str,
    payload: dict,
    publish: bool = False,
) -> dict:
    """Create article via articleCreate mutation."""

    mutation = """
    mutation CreateArticle($article: ArticleCreateInput!) {
      articleCreate(article: $article) {
        article {
          id
          handle
          title
        }
        userErrors {
          field
          message
          code
        }
      }
    }
    """

    # Build article input
    tags = payload.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    article_input = {
        "blogId": blog_id,
        "title": payload["title"],
        "author": {"name": payload.get("author_name", "The Rike")},
        "body": payload["body_html"],
        "summary": payload.get("meta_desc", ""),
        "isPublished": publish,
        "tags": tags,
    }

    # Add handle if provided
    if payload.get("handle"):
        article_input["handle"] = payload["handle"]

    # Add image if provided
    if payload.get("featured_image_url"):
        article_input["image"] = {
            "url": payload["featured_image_url"],
            "altText": payload.get("featured_image_alt", ""),
        }

    data = gql(shop, token, api_version, mutation, {"article": article_input})
    result = data.get("articleCreate", {})

    if result.get("userErrors"):
        raise RuntimeError(f"Article creation errors: {result['userErrors']}")

    return result.get("article", {})


def set_metafields(
    shop: str, token: str, api_version: str, owner_id: str, metafields: list
) -> dict:
    """Set metafields on article."""

    mutation = """
    mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
      metafieldsSet(metafields: $metafields) {
        metafields {
          namespace
          key
          type
          value
        }
        userErrors {
          field
          message
          code
        }
      }
    }
    """

    # Build metafield inputs
    mf_inputs = []
    for mf in metafields:
        mf_inputs.append(
            {
                "ownerId": owner_id,
                "namespace": mf["namespace"],
                "key": mf["key"],
                "type": mf.get("type", "single_line_text_field"),
                "value": (
                    mf["value"]
                    if isinstance(mf["value"], str)
                    else json.dumps(mf["value"])
                ),
            }
        )

    if not mf_inputs:
        return {}

    data = gql(shop, token, api_version, mutation, {"metafields": mf_inputs})
    result = data.get("metafieldsSet", {})

    if result.get("userErrors"):
        raise RuntimeError(f"Metafield errors: {result['userErrors']}")

    return result


def compute_fingerprint(payload: dict) -> str:
    """Compute fingerprint hash for deduplication."""
    # Use topic + primary keyword + title for fingerprint
    data = f"{payload.get('topic', '')}-{payload.get('primary_keyword', '')}-{payload.get('title', '')}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:32]


def main(payload_path: str):
    """Main publish function."""
    config = load_config()

    # Check QA report for pass status
    qa_report_path = CONTENT_DIR / "qa_report.json"
    if qa_report_path.exists():
        qa = json.loads(qa_report_path.read_text(encoding="utf-8"))

        if not qa.get("validator_pass"):
            print("REFUSING TO PUBLISH: validator_pass is not true")
            sys.exit(3)

        if not qa.get("reviewer_pass"):
            print("REFUSING TO PUBLISH: reviewer_pass is not true")
            sys.exit(3)
    else:
        print("WARNING: No qa_report.json found. Proceeding with caution.")

    # Load payload
    try:
        with open(payload_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        print(f"PUBLISH FAIL: Cannot load payload: {e}")
        sys.exit(2)

    # Get Shopify credentials
    shop = get_env_with_fallback(
        "SHOPIFY_STORE_DOMAIN", config.get("shop", {}).get("domain")
    )
    token = get_env_with_fallback(
        "SHOPIFY_ADMIN_ACCESS_TOKEN", config.get("shop", {}).get("access_token")
    )
    api_version = get_env_with_fallback(
        "SHOPIFY_API_VERSION", config.get("shop", {}).get("api_version", "2025-10")
    )

    if not shop or not token:
        print(
            "PUBLISH FAIL: Missing SHOPIFY_STORE_DOMAIN or SHOPIFY_ADMIN_ACCESS_TOKEN"
        )
        sys.exit(2)

    # Get blog ID
    blog_handle = payload.get(
        "blog_handle",
        config.get("defaults", {}).get("blog_handle", "sustainable-living"),
    )
    blog_id = get_blog_id_by_handle(shop, token, api_version, blog_handle)
    print(f"Found blog: {blog_handle} -> {blog_id}")

    # Compute fingerprint for idempotency
    fingerprint = compute_fingerprint(payload)
    mf_config = config.get("metafields", {})
    fp_namespace = mf_config.get("fingerprint_namespace", "pipeline")
    fp_key = mf_config.get("fingerprint_key", "fingerprint")

    # Check for duplicate
    existing = check_duplicate_by_fingerprint(
        shop, token, api_version, blog_id, fingerprint, fp_namespace, fp_key
    )

    if existing:
        print(
            f"DUPLICATE FOUND: Article already exists with handle '{existing['handle']}'"
        )
        print(f"Article ID: {existing['id']}")

        # Write result
        result = {
            "status": "duplicate",
            "article_id": existing["id"],
            "handle": existing["handle"],
            "title": existing["title"],
            "fingerprint": fingerprint,
        }
        (CONTENT_DIR / "publish_result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        sys.exit(0)

    # Determine publish mode
    publish_mode = payload.get(
        "publish", config.get("defaults", {}).get("publish_mode", "draft")
    )
    is_published = publish_mode in [True, "true", "publish", "published"]

    # Create article
    print(f"Creating article: {payload['title']}")
    article = create_article(shop, token, api_version, blog_id, payload, is_published)
    print(f"Created article: {article['id']}")

    # Set metafields
    metafields = []

    # Schema JSON-LD
    if payload.get("schema_jsonld"):
        metafields.append(
            {
                "namespace": mf_config.get("schema_namespace", "seo"),
                "key": mf_config.get("schema_key", "schema_jsonld"),
                "type": "json",
                "value": payload["schema_jsonld"],
            }
        )

    # Fingerprint
    metafields.append(
        {
            "namespace": fp_namespace,
            "key": fp_key,
            "type": "single_line_text_field",
            "value": fingerprint,
        }
    )

    # Evidence digest
    evidence_path = CONTENT_DIR / "evidence_ledger.json"
    if evidence_path.exists():
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence_digest = {
            "sources_count": len(evidence.get("sources", [])),
            "stats_count": len(evidence.get("stats", [])),
            "quotes_count": len(evidence.get("quotes", [])),
        }
        metafields.append(
            {
                "namespace": mf_config.get("evidence_namespace", "pipeline"),
                "key": mf_config.get("evidence_key", "evidence_digest"),
                "type": "json",
                "value": evidence_digest,
            }
        )

    if metafields:
        set_metafields(shop, token, api_version, article["id"], metafields)
        print(f"Set {len(metafields)} metafields")

    # Write result
    result = {
        "status": "published" if is_published else "draft",
        "article_id": article["id"],
        "handle": article["handle"],
        "title": article["title"],
        "blog_handle": blog_handle,
        "fingerprint": fingerprint,
        "timestamp": int(time.time()),
    }

    (CONTENT_DIR / "publish_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nPUBLISHED: {result}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/publish_article.py content/article_payload.json")
        sys.exit(1)
    main(sys.argv[1])
