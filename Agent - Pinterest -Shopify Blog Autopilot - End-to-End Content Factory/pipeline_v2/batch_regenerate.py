#!/usr/bin/env python3
"""
Batch regenerate articles that have TEMPLATE GARBAGE content.
This script regenerates content using Gemini API and updates Shopify directly.

Usage:
  python batch_regenerate.py                    # Regenerate all garbage articles
  python batch_regenerate.py --max 5            # Regenerate max 5 articles
  python batch_regenerate.py --interval 600     # 10 minute intervals (default)
  python batch_regenerate.py --dry-run          # Print what would run
  python batch_regenerate.py --ids 123,456,789  # Specific IDs only
"""

import os
import sys
import time
import re
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# Load environment
try:
    from dotenv import load_dotenv

    for p in [Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if p.exists():
            load_dotenv(p)
            break
except ImportError:
    pass

# API Keys
API_KEY = (
    os.getenv("GOOGLE_AI_STUDIO_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or "***REDACTED***"
)

SHOPIFY_STORE = "https://" + os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID")


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def call_gemini(prompt: str, max_tokens: int = 8000) -> str:
    """Call Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": max_tokens,
            "topP": 0.9,
        },
    }

    response = requests.post(url, json=payload, timeout=120)

    if response.status_code != 200:
        log(f"Gemini error: {response.status_code}")
        return None

    result = response.json()
    try:
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return None


def generate_article_content(title: str, tags: str = "") -> str:
    """Generate proper article content based on title."""

    # Parse title to understand topic
    title_lower = title.lower()

    # Determine article type and create appropriate prompt
    if any(x in title_lower for x in ["diy", "homemade", "recipe", "make"]):
        article_type = "DIY/Recipe guide"
    elif any(x in title_lower for x in ["grow", "growing", "plant", "garden"]):
        article_type = "Gardening guide"
    elif any(
        x in title_lower for x in ["health", "benefit", "uses", "remedy", "relief"]
    ):
        article_type = "Health and wellness guide"
    elif any(x in title_lower for x in ["build", "step-by-step", "how to"]):
        article_type = "Step-by-step tutorial"
    else:
        article_type = "Informational guide"

    prompt = f"""You are an expert content writer for a Shopify blog about home gardening, herbal remedies, and sustainable living.

Write a comprehensive, SEO-optimized blog article for the following topic:

TITLE: {title}
TAGS: {tags}
ARTICLE TYPE: {article_type}

REQUIREMENTS:
1. Write in an engaging, informative, and practical style
2. Include specific, actionable advice that readers can actually use
3. Use proper HTML formatting: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>
4. Target word count: 1500-2000 words
5. Include multiple sections with clear headings
6. Add practical tips, common mistakes to avoid, and expert recommendations
7. Make content unique and valuable - NO generic placeholder content
8. Include specific measurements, timings, and quantities where applicable

STRUCTURE:
- Start with an engaging introduction (what/why/benefits)
- Include step-by-step instructions or detailed explanations
- Add practical tips and common mistakes
- Include safety notes or precautions if relevant
- End with a helpful conclusion

CRITICAL:
- Write REAL, SPECIFIC, ACTIONABLE content
- Do NOT use placeholder phrases like "works best when you keep the steps specific to [topic]"
- Do NOT repeat the title as filler text
- Do NOT include generic "Key Terms" or "Sources" sections at the end

OUTPUT: Return ONLY the HTML content, starting with the first <h2> tag. No markdown code blocks."""

    content = call_gemini(prompt)

    if content:
        # Clean up any markdown code blocks
        content = re.sub(r"^```html?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
        content = content.strip()

    return content


def get_article(article_id: int) -> dict:
    """Get article from Shopify."""
    url = (
        f"{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    )
    headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN}

    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 200:
        return response.json().get("article", {})
    return {}


def update_article(article_id: int, body_html: str) -> bool:
    """Update article on Shopify."""
    url = (
        f"{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    )
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }

    data = {"article": {"id": article_id, "body_html": body_html}}
    response = requests.put(url, headers=headers, json=data, timeout=30)
    return response.status_code == 200


def validate_content(content: str, title: str) -> bool:
    """Validate generated content is not garbage."""
    if not content or len(content) < 1000:
        return False

    soup = BeautifulSoup(content, "html.parser")
    text = soup.get_text(" ", strip=True).lower()

    # Check for garbage patterns
    garbage_patterns = [
        "works best when you",
        "key conditions at a glance",
        "adjust one variable at a time",
        "align steps and inputs",
    ]

    for pattern in garbage_patterns:
        if pattern in text:
            return False

    # Check title not repeated excessively
    title_clean = re.sub(r"[^a-z0-9 ]", "", title.lower())
    title_words = [w for w in title_clean.split() if len(w) > 5]

    if title_words:
        phrase = " ".join(title_words[:3])
        if text.count(phrase) > 5:
            return False

    return True


def load_garbage_list() -> list:
    """Load list of garbage article IDs."""
    file_path = Path(__file__).parent / "articles_need_regen.txt"
    if not file_path.exists():
        return []

    with open(file_path, "r") as f:
        return [int(line.strip()) for line in f if line.strip().isdigit()]


def regenerate_article(article_id: int, dry_run: bool = False) -> bool:
    """Regenerate a single article."""
    log(f"Processing article {article_id}...")

    # Get current article
    article = get_article(article_id)
    if not article:
        log(f"  ❌ Failed to fetch article {article_id}")
        return False

    title = article.get("title", "")
    tags = article.get("tags", "")
    current_body = article.get("body_html", "")

    log(f"  Title: {title[:50]}...")
    log(f"  Current body: {len(current_body)} chars")

    if dry_run:
        log(f"  [DRY-RUN] Would regenerate content")
        return True

    # Generate new content
    log(f"  Generating new content with Gemini...")
    new_content = generate_article_content(title, tags)

    if not new_content:
        log(f"  ❌ Failed to generate content")
        return False

    log(f"  Generated: {len(new_content)} chars")

    # Validate content
    if not validate_content(new_content, title):
        log(f"  ⚠️ Generated content may still be garbage, retrying...")
        # Retry once with explicit anti-garbage instruction
        new_content = generate_article_content(
            title + " - IMPORTANT: Write real helpful content, not template garbage",
            tags,
        )
        if not new_content or not validate_content(new_content, title):
            log(f"  ❌ Failed validation after retry")
            return False

    # Update article
    log(f"  Updating Shopify...")
    if update_article(article_id, new_content):
        log(f"  ✅ Article updated successfully!")
        return True
    else:
        log(f"  ❌ Failed to update article")
        return False


def main():
    parser = argparse.ArgumentParser(description="Batch regenerate garbage articles")
    parser.add_argument(
        "--max", type=int, default=100, help="Maximum articles to process"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=600,
        help="Seconds between articles (default: 600 = 10 min)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would be done"
    )
    parser.add_argument("--ids", type=str, help="Comma-separated list of specific IDs")
    args = parser.parse_args()

    log("=" * 60)
    log("BATCH ARTICLE REGENERATION")
    log("=" * 60)

    # Get article IDs
    if args.ids:
        article_ids = [int(x.strip()) for x in args.ids.split(",")]
    else:
        article_ids = load_garbage_list()

    if not article_ids:
        log("No articles to process. Run classify_articles.py first.")
        return

    log(f"Found {len(article_ids)} articles to regenerate")
    log(f"Max: {args.max}, Interval: {args.interval}s ({args.interval/60:.1f} min)")
    log(
        f"Estimated time: {min(len(article_ids), args.max) * args.interval / 60:.0f} minutes"
    )

    if args.dry_run:
        log("[DRY-RUN MODE]")

    log("")

    # Process articles
    success = 0
    failed = 0

    for i, article_id in enumerate(article_ids[: args.max]):
        log(f"\n[{i+1}/{min(len(article_ids), args.max)}] Article {article_id}")

        if regenerate_article(article_id, args.dry_run):
            success += 1
        else:
            failed += 1

        # Wait before next article (except for last one)
        if i < min(len(article_ids), args.max) - 1:
            log(
                f"\n⏳ Waiting {args.interval}s ({args.interval/60:.1f} min) before next article..."
            )
            if not args.dry_run:
                time.sleep(args.interval)

    # Summary
    log("\n" + "=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"✅ Success: {success}")
    log(f"❌ Failed: {failed}")
    log(f"Total processed: {success + failed}")


if __name__ == "__main__":
    main()
