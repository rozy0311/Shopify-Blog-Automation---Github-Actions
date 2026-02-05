#!/usr/bin/env python3
"""
Automated Product Content Generator & Pusher
=============================================
Continues generating high-quality content for remaining products
and pushes to Shopify automatically.

Usage:
    python auto_content_runner.py [--batch-size N] [--start-index N] [--dry-run]

This script:
1. Loads products that don't have content yet
2. Generates content using template structure
3. Saves to high_quality_content folder
4. Pushes to Shopify
5. Logs progress for resume capability
"""

import json
import time
import argparse
import os
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

SHOP = os.getenv("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
API_VERSION = "2025-01"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

BASE_DIR = Path(__file__).parent
CONTENT_DIR = BASE_DIR / "high_quality_content"
CACHE_DIR = BASE_DIR / "cache"
LOGS_DIR = BASE_DIR / "logs"
PROGRESS_FILE = LOGS_DIR / "automation_progress.json"

# Ensure directories exist
CONTENT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ============================================================================
# CONTENT TEMPLATES
# ============================================================================


def get_product_category(title: str) -> str:
    """Determine product category from title"""
    title_lower = title.lower()

    if any(x in title_lower for x in ["seed", "seeds", "planting"]):
        return "seeds"
    elif any(x in title_lower for x in ["tea", "herbal", "leaf", "leaves", "tisane"]):
        return "tea"
    elif any(x in title_lower for x in ["powder", "ground", "turmeric", "curcumin"]):
        return "powder"
    elif any(x in title_lower for x in ["spice", "clove", "cinnamon", "pepper"]):
        return "spice"
    elif any(x in title_lower for x in ["dried", "dehydrated", "flakes"]):
        return "dried_goods"
    elif any(
        x in title_lower for x in ["hair", "wash", "soap", "detergent", "shampoo"]
    ):
        return "personal_care"
    else:
        return "general"


def extract_quantity(title: str) -> str:
    """Extract quantity from title (e.g., '100g', '100 seeds', '1000')"""
    import re

    # Match patterns like "100g", "100 gram", "100 seeds", "1000"
    patterns = [
        r"(\d+)\s*(g|gram|grams)\b",
        r"(\d+)\s*(seeds|seed)\b",
        r"(\d+)\s*(pack|packs)\b",
        r"^(\d+)\s+",
    ]

    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return ""


def generate_content_structure(product: dict) -> dict:
    """
    Generate content structure for a product.

    NOTE: This creates a template structure. For truly high-quality content,
    you would want to:
    1. Use an LLM API (OpenAI, Claude, etc.) to generate the actual text
    2. Or manually review and enhance each product

    This template ensures the structure is correct for the Meta-Prompt format.
    """

    title = product["title"]
    product_id = product["id"]
    category = get_product_category(title)
    quantity = extract_quantity(title)

    # Base template - content needs enhancement
    content = {
        "product_id": product_id,
        "original_title": title,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "quality": "template_generated",
        "needs_review": True,
        "content": {
            "title": title,
            "direct_answer": f"[NEEDS CONTENT] {title} - Direct answer with product name and key specs in first 35-55 words.",
            "short_desc": f"[NEEDS CONTENT] Story about {title} - Sensory details, cozy tone, 80-120 words.",
            "highlights": [
                f"[NEEDS CONTENT] Highlight 1 for {title}",
                "[NEEDS CONTENT] Highlight 2",
                "[NEEDS CONTENT] Highlight 3",
                "[NEEDS CONTENT] Highlight 4",
                "[NEEDS CONTENT] Highlight 5",
                "[NEEDS CONTENT] Highlight 6",
            ],
            "how_to": [
                "[NEEDS CONTENT] Step 1 with specific measurements",
                "[NEEDS CONTENT] Step 2",
                "[NEEDS CONTENT] Step 3",
                "[NEEDS CONTENT] Step 4",
                "[NEEDS CONTENT] Step 5",
                "[NEEDS CONTENT] Step 6",
            ],
            "specs": f"[NEEDS CONTENT] Net weight: {quantity}. Form: [form]. Origin: [origin]. Shelf life: [shelf life].",
            "whats_included": [
                f"[NEEDS CONTENT] {quantity} [product type]",
                "[NEEDS CONTENT] Resealable pouch",
            ],
            "care_storage": "[NEEDS CONTENT] Storage instructions with specific conditions.",
            "variants": "ΓÇö",
            "key_terms": [
                "[NEEDS CONTENT] Term 1 ΓÇö Definition",
                "[NEEDS CONTENT] Term 2 ΓÇö Definition",
                "[NEEDS CONTENT] Term 3 ΓÇö Definition",
            ],
            "who_should_not": [],
            "cozy_note": f"[NEEDS CONTENT] Personal, sensory cozy note about {title}",
            "certs_labels": ["All-Natural"],
            "sources_mention": "[NEEDS CONTENT] Sources",
            "meta_title": f"[NEEDS SEO] {title[:50]} | Category",
            "meta_description": f"[NEEDS SEO] Shop {title}. Key benefits. 120-155 chars.",
            "body_html": f"<article><p>[NEEDS CONTENT] Full HTML body for {title}</p></article>",
        },
    }

    return content


# ============================================================================
# SHOPIFY PUSH FUNCTIONS
# ============================================================================


def push_content_to_shopify(content_data: dict) -> bool:
    """Push content to Shopify"""

    product_id = content_data["product_id"]
    content = content_data["content"]

    # Skip if marked as needs review
    if content_data.get("needs_review"):
        print(f"  ΓÅ¡∩╕Å Skipping (needs review): {content['title'][:50]}")
        return False

    print(f"\nPushing: {content['title'][:50]}...")

    # Update product body_html only
    url = f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}.json"
    product_data = {
        "product": {"id": product_id, "body_html": content.get("body_html", "")}
    }

    try:
        response = requests.put(url, headers=HEADERS, json=product_data, timeout=30)
        if response.status_code != 200:
            print(f"  Γ¥î Failed: {response.status_code}")
            return False
        print(f"  Γ£à Updated body_html")
    except Exception as e:
        print(f"  Γ¥î Error: {e}")
        return False

    # Update metafields
    metafields = build_metafields(content)
    for mf in metafields:
        success = update_metafield(product_id, mf)
        status = "Γ£à" if success else "ΓÜá∩╕Å"
        print(f"  {status} Metafield: {mf['key']}")
        time.sleep(0.1)

    return True


def build_metafields(content: dict) -> list:
    """Build metafields from content"""
    metafields = []

    text_fields = [
        ("direct_answer", "multi_line_text_field"),
        ("short_desc", "multi_line_text_field"),
        ("specs", "multi_line_text_field"),
        ("care_storage", "multi_line_text_field"),
        ("cozy_note", "multi_line_text_field"),
        ("sources_mention", "single_line_text_field"),
        ("meta_title", "single_line_text_field"),
        ("meta_description", "multi_line_text_field"),
    ]

    for key, field_type in text_fields:
        if content.get(key) and not content[key].startswith("[NEEDS"):
            metafields.append(
                {
                    "namespace": "custom",
                    "key": key,
                    "value": content[key],
                    "type": field_type,
                }
            )

    json_fields = [
        "highlights",
        "how_to",
        "whats_included",
        "key_terms",
        "who_should_not",
        "certs_labels",
    ]
    for key in json_fields:
        if content.get(key) and content[key]:
            # Skip if any item starts with [NEEDS
            if any(str(item).startswith("[NEEDS") for item in content[key]):
                continue
            metafields.append(
                {
                    "namespace": "custom",
                    "key": key,
                    "value": json.dumps(content[key]),
                    "type": "json",
                }
            )

    return metafields


def update_metafield(product_id: int, metafield: dict) -> bool:
    """Update or create a metafield"""
    get_url = (
        f"https://{SHOP}/admin/api/{API_VERSION}/products/{product_id}/metafields.json"
    )

    try:
        existing = requests.get(get_url, headers=HEADERS, timeout=30).json()

        existing_mf = None
        for mf in existing.get("metafields", []):
            if (
                mf["namespace"] == metafield["namespace"]
                and mf["key"] == metafield["key"]
            ):
                existing_mf = mf
                break

        if existing_mf:
            update_url = f"https://{SHOP}/admin/api/{API_VERSION}/metafields/{existing_mf['id']}.json"
            resp = requests.put(
                update_url,
                headers=HEADERS,
                json={"metafield": {"value": metafield["value"]}},
                timeout=30,
            )
            return resp.status_code == 200
        else:
            resp = requests.post(
                get_url, headers=HEADERS, json={"metafield": metafield}, timeout=30
            )
            return resp.status_code in [200, 201]
    except Exception as e:
        return False


# ============================================================================
# PROGRESS TRACKING
# ============================================================================


def load_progress() -> dict:
    """Load progress from file"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "completed_ids": [],
        "failed_ids": [],
        "last_run": None,
        "total_processed": 0,
    }


def save_progress(progress: dict):
    """Save progress to file"""
    progress["last_run"] = datetime.utcnow().isoformat()
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


def get_remaining_products() -> list:
    """Get products that haven't been processed yet"""

    # Load all products
    products_file = CACHE_DIR / "active_products.json"
    if not products_file.exists():
        print("Γ¥î No products cache found. Run fetch_products.py first.")
        return []

    with open(products_file, "r", encoding="utf-8") as f:
        all_products = json.load(f)

    # Get already processed IDs
    existing_content_ids = set()
    for content_file in CONTENT_DIR.glob("content_*.json"):
        try:
            with open(content_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Only count if it's high quality (not template)
                if data.get("quality") == "manual_high":
                    existing_content_ids.add(data["product_id"])
        except:
            pass

    # Filter to remaining products
    remaining = [p for p in all_products if p["id"] not in existing_content_ids]

    return remaining


# ============================================================================
# MAIN
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Automated Product Content Generator")
    parser.add_argument("--batch-size", type=int, default=5, help="Products per batch")
    parser.add_argument("--start-index", type=int, default=0, help="Start from index")
    parser.add_argument(
        "--dry-run", action="store_true", help="Generate templates only, don't push"
    )
    parser.add_argument(
        "--list-remaining", action="store_true", help="Just list remaining products"
    )
    args = parser.parse_args()

    remaining = get_remaining_products()

    print("=" * 70)
    print("AUTOMATED PRODUCT CONTENT GENERATOR")
    print("=" * 70)
    print(f"Total remaining products: {len(remaining)}")
    print(f"Batch size: {args.batch_size}")
    print(f"Start index: {args.start_index}")
    print("=" * 70)

    if args.list_remaining:
        for i, p in enumerate(remaining[:50]):
            print(f"{i+1}. {p['title'][:70]} | ID:{p['id']}")
        if len(remaining) > 50:
            print(f"... and {len(remaining) - 50} more")
        return

    # Process batch
    batch = remaining[args.start_index : args.start_index + args.batch_size]

    if not batch:
        print("Γ£à No more products to process!")
        return

    print(f"\nProcessing batch of {len(batch)} products:\n")

    for product in batch:
        print(f"≡ƒôª {product['title'][:60]}")

        # Generate template
        content = generate_content_structure(product)

        # Save to file
        output_file = CONTENT_DIR / f"content_{product['id']}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)

        print(f"   ≡ƒÆ╛ Template saved: {output_file.name}")

        if not args.dry_run and content.get("quality") == "manual_high":
            success = push_content_to_shopify(content)
            status = "Γ£à" if success else "Γ¥î"
            print(f"   {status} Pushed to Shopify")
        else:
            print(f"   ΓÅ¡∩╕Å Skipping push (template needs content)")

    print("\n" + "=" * 70)
    print("BATCH COMPLETE")
    print("=" * 70)
    print(f"Processed: {len(batch)} products")
    print(f"Remaining: {len(remaining) - len(batch)}")
    print(f"\nNext batch command:")
    print(
        f"  python auto_content_runner.py --start-index {args.start_index + args.batch_size}"
    )
    print("\nΓÜá∩╕Å IMPORTANT: Generated templates need manual content enhancement!")
    print(
        "   Edit the JSON files in high_quality_content/ then run push_high_quality.py"
    )


if __name__ == "__main__":
    main()
