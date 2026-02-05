"""
Batch Process Blogs with Evidence-Based Pipeline V2
Processes draft articles one by one with real research
"""

import json
import re
import os
import time
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Configuration
SHOP = os.getenv("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")
API_VERSION = "2025-01"

BASE_DIR = Path(__file__).parent
PROGRESS_FILE = BASE_DIR / "batch_progress.json"
DRAFTS_FILE = BASE_DIR / "drafts_to_process.json"
OUTPUT_DIR = BASE_DIR / "generated_articles"

# Ensure output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)


def load_progress():
    """Load batch progress from file"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"processed": [], "failed": [], "skipped": [], "last_run": None}


def save_progress(progress):
    """Save batch progress to file"""
    progress["last_run"] = datetime.now().isoformat()
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


def load_drafts():
    """Load draft articles list"""
    if DRAFTS_FILE.exists():
        with open(DRAFTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def extract_topic_keywords(title):
    """Extract search keywords from article title"""
    # Remove common words and clean up
    stop_words = {
        "how",
        "to",
        "the",
        "a",
        "an",
        "in",
        "on",
        "at",
        "for",
        "with",
        "and",
        "or",
        "of",
        "is",
        "are",
        "this",
        "that",
        "your",
        "you",
    }
    words = title.lower().split()
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    return " ".join(keywords[:6])


def generate_article_stub(article_id, title, handle):
    """
    Generate a stub for the article that needs to be processed.
    This is a placeholder - the actual content generation would be done
    by the agent using web search and fetch_webpage tools.
    """
    keywords = extract_topic_keywords(title)

    return {
        "id": article_id,
        "title": title,
        "handle": handle,
        "search_keywords": keywords,
        "status": "needs_research",
        "timestamp": datetime.now().isoformat(),
        "research_queries": [
            f"{keywords} guide tutorial",
            f"{keywords} benefits tips",
            f"{keywords} step by step how to",
        ],
    }


def process_single_article(article):
    """
    Process a single article - creates a stub file for agent processing
    """
    article_id = article["id"]
    title = article["title"]
    handle = article["handle"]

    print(f"\n{'='*60}")
    print(f"Processing: {title[:50]}...")
    print(f"ID: {article_id}")

    # Generate stub
    stub = generate_article_stub(article_id, title, handle)

    # Save stub for agent processing
    safe_handle = handle[:50] if handle else str(article_id)
    safe_handle = re.sub(r'[<>:"/\\|?*]', "_", safe_handle)

    stub_file = OUTPUT_DIR / f"{safe_handle}_stub.json"
    with open(stub_file, "w", encoding="utf-8") as f:
        json.dump(stub, f, indent=2, ensure_ascii=False)

    print(f"Created stub: {stub_file.name}")
    print(f"Search keywords: {stub['search_keywords']}")

    return {
        "id": article_id,
        "title": title,
        "stub_file": str(stub_file),
        "status": "stub_created",
    }


def main():
    print("=" * 60)
    print("BATCH BLOG PROCESSOR - Pipeline V2")
    print("=" * 60)

    # Load progress and drafts
    progress = load_progress()
    drafts = load_drafts()

    if not drafts:
        print("No drafts found. Run the main script first to fetch drafts.")
        return

    # Filter out already processed
    processed_ids = set(
        progress["processed"] + progress["failed"] + progress["skipped"]
    )
    remaining = [d for d in drafts if d["id"] not in processed_ids]

    print(f"\nTotal drafts: {len(drafts)}")
    print(f"Already processed: {len(processed_ids)}")
    print(f"Remaining: {len(remaining)}")

    if not remaining:
        print("\nΓ£à All articles have been processed!")
        return

    # Process first 10 articles (batch size)
    batch_size = 10
    batch = remaining[:batch_size]

    print(f"\nProcessing batch of {len(batch)} articles...")

    for article in batch:
        try:
            result = process_single_article(article)
            progress["processed"].append(article["id"])
            print(f"Γ£à Success")
        except Exception as e:
            print(f"Γ¥î Failed: {e}")
            progress["failed"].append(article["id"])

    # Save progress
    save_progress(progress)

    print(f"\n{'='*60}")
    print("BATCH COMPLETE")
    print(f"Processed: {len(progress['processed'])}")
    print(f"Failed: {len(progress['failed'])}")
    print(
        f"Remaining: {len(drafts) - len(progress['processed']) - len(progress['failed'])}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
