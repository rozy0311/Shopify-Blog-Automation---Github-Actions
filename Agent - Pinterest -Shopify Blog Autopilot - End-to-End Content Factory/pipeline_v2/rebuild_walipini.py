#!/usr/bin/env python3
"""
Rebuild article 690525110590 - Walipini Greenhouse Build Guide
The LLM previously misunderstood this topic and created content about "growing walipini" as if it were a plant.
This script regenerates the content with a VERY CLEAR prompt.
"""

import os
import sys
import json
import re
import requests
from dotenv import load_dotenv

# Load environment
load_dotenv()

# API Keys - NEVER hardcode keys, always use environment variables
API_KEY = (
    os.getenv("GOOGLE_AI_STUDIO_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or os.getenv("FALLBACK_GOOGLE_AI_STUDIO_API_KEY")
    or os.getenv("FALLBACK_GEMINI_API_KEY")
    or os.getenv("SECOND_FALLBACK_GOOGLE_AI_STUDIO_API_KEY")
    or os.getenv("SECOND_FALLBACK_GEMINI_API_KEY")
    or os.getenv("GEMINI_API_KEY_3")
    or os.getenv("THIRD_GEMINI_API_KEY")
    or ""
)
if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY or GOOGLE_AI_STUDIO_API_KEY must be set in environment"
    )

SHOPIFY_STORE = "https://" + os.getenv("SHOPIFY_STORE_DOMAIN", "").strip()
SHOPIFY_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID")
ARTICLE_ID = 690525110590


def call_gemini(prompt: str, max_tokens: int = 8000) -> str:
    """Call Gemini API with the given prompt."""
    # Use header-based auth instead of URL query param for security
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": max_tokens,
            "topP": 0.9,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY,
    }

    print("Calling Gemini API...")
    response = requests.post(url, headers=headers, json=payload, timeout=120)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text[:500])
        return None

    result = response.json()
    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        return text
    except (KeyError, IndexError) as e:
        print(f"Error parsing response: {e}")
        print(json.dumps(result, indent=2)[:500])
        return None


def generate_walipini_content():
    """Generate proper content for Walipini greenhouse article."""

    # VERY CLEAR prompt to prevent misunderstanding
    prompt = """You are an expert gardening and sustainable living content writer for a Shopify blog about home gardening.

CRITICAL CLARIFICATION - READ CAREFULLY:
- A "Walipini" is a TYPE OF UNDERGROUND GREENHOUSE structure, also known as a "pit greenhouse" or "earth-sheltered greenhouse"
- It is NOT a plant, vegetable, or fruit
- "Walipini" is a word from Aymara (indigenous South American language) meaning "place of warmth"
- This article is about HOW TO BUILD a Walipini underground greenhouse structure

Write a comprehensive, SEO-optimized blog article about:

TOPIC: How to Build a Walipini Underground Greenhouse for Year-Round Food Growing

TARGET AUDIENCE: Beginner homesteaders and gardeners interested in sustainable, off-grid food production

ARTICLE STRUCTURE:
1. Introduction - What is a Walipini? (underground greenhouse structure from Bolivia)
2. Benefits of building a Walipini:
   - Uses geothermal energy from the earth
   - Passive solar heating through angled roof
   - Grow food year-round even in cold climates
   - Low-cost construction compared to traditional greenhouses
   - No heating bills

3. Site Selection for Your Walipini:
   - South-facing slope (northern hemisphere)
   - Water table depth considerations
   - Soil drainage requirements
   - Avoiding underground utilities

4. Materials Needed:
   - Clear roofing material (polycarbonate, greenhouse plastic)
   - Adobe/rammed earth or concrete blocks for walls
   - Lumber for roof frame
   - Drainage materials

5. Step-by-Step Building Process:
   - Excavation depth (typically 6-8 feet deep)
   - Wall construction
   - Roof angle calculation for your latitude
   - Ventilation system
   - Drainage installation

6. What to Grow in Your Walipini:
   - Cold-hardy vegetables
   - Year-round greens
   - Citrus in cold climates

7. Maintenance Tips

8. Common Mistakes to Avoid

9. Conclusion with call-to-action

FORMATTING REQUIREMENTS:
- Use proper HTML tags: <h2>, <h3>, <p>, <ul>, <li>, <strong>, <em>
- Include 2-3 relevant internal links placeholders: [INTERNAL_LINK: topic]
- Make it engaging, practical, and actionable
- Target word count: 1800-2200 words
- Include specific measurements and practical tips
- Do NOT include generic placeholder sections like "Sources" or "Key Terms" at the end

OUTPUT: Return ONLY the HTML content, starting with the first <h2> tag. No markdown, no code blocks."""

    content = call_gemini(prompt)
    return content


def update_shopify_article(body_html: str) -> bool:
    """Update the article on Shopify."""
    url = (
        f"{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{ARTICLE_ID}.json"
    )
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }

    # Clean up any markdown code blocks if present
    body_html = re.sub(r"^```html?\s*", "", body_html)
    body_html = re.sub(r"\s*```$", "", body_html)
    body_html = body_html.strip()

    data = {"article": {"id": ARTICLE_ID, "body_html": body_html}}

    print(f"Updating article {ARTICLE_ID}...")
    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 200:
        print(f"✅ Article updated successfully!")
        print(f"   New body length: {len(body_html)} chars")
        return True
    else:
        print(f"❌ Failed to update: {response.status_code}")
        print(response.text[:500])
        return False


def publish_article() -> bool:
    """Publish the article."""
    url = (
        f"{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{ARTICLE_ID}.json"
    )
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }

    # Fetch current article to check if already published
    get_resp = requests.get(url, headers=headers, timeout=30)
    if get_resp.status_code == 200:
        existing = get_resp.json().get("article", {})
        existing_pub = existing.get("published_at")
        if existing_pub:
            print(f"[SKIP] Article already published at {existing_pub} — keeping original date.")
            return True

    from datetime import datetime

    data = {
        "article": {
            "id": ARTICLE_ID,
            "published_at": datetime.utcnow().isoformat() + "Z",
        }
    }

    print("Publishing article (first time)...")
    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 200:
        print("✅ Article published!")
        return True
    else:
        print(f"❌ Failed to publish: {response.status_code}")
        return False


def main():
    print("=" * 60)
    print("REBUILDING ARTICLE: Walipini Greenhouse Build Guide")
    print("=" * 60)
    print()

    # Generate new content
    print("Step 1: Generating new content with Gemini...")
    content = generate_walipini_content()

    if not content:
        print("❌ Failed to generate content")
        return False

    print(f"✅ Generated {len(content)} chars of content")
    print()

    # Validate content - make sure it talks about BUILDING, not growing walipini
    content_lower = content.lower()

    # Check for signs of correct content
    good_signs = [
        "underground greenhouse",
        "pit greenhouse",
        "excavat",
        "construct",
        "build",
        "roof",
        "geothermal",
        "earth-sheltered",
        "dig",
    ]
    good_count = sum(1 for sign in good_signs if sign in content_lower)

    # Check for signs of wrong content (treating walipini as a plant)
    bad_signs = [
        "grow walipini",
        "plant walipini",
        "harvest walipini",
        "walipini seeds",
        "walipini fruit",
        "eating walipini",
    ]
    bad_count = sum(1 for sign in bad_signs if sign in content_lower)

    print(
        f"Content validation: {good_count} good indicators, {bad_count} bad indicators"
    )

    if bad_count > 0:
        print(
            "⚠️ WARNING: Content may still be incorrect (treating Walipini as a plant)"
        )
        print("First 500 chars of generated content:")
        print(content[:500])
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != "y":
            return False

    if good_count < 3:
        print("⚠️ WARNING: Content may not be about building a greenhouse")
        print("First 500 chars:")
        print(content[:500])

    # Update article
    print()
    print("Step 2: Updating Shopify article...")
    if not update_shopify_article(content):
        return False

    # Ask about publishing
    print()
    response = input("Publish the article now? (y/n): ")
    if response.lower() == "y":
        publish_article()
    else:
        print("Article saved as draft (not published)")

    print()
    print("=" * 60)
    print("REBUILD COMPLETE!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
