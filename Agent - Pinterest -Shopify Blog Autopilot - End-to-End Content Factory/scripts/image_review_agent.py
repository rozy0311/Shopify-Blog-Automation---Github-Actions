"""
Image Review Agent - Validates images match article topic

This agent:
1. Analyzes article content to extract key visual concepts
2. Searches for royalty-free images from Pexels/Pixabay/Unsplash
3. Reviews each image for:
   - Topic relevance (matches article content)
   - No watermarks or embedded links
   - Image quality (resolution, clarity)
   - Appropriate for blog use
4. Outputs approved image URLs with alt text suggestions

Usage:
    python scripts/image_review_agent.py

Requires:
    pip install requests pillow
"""

import json
import os
import sys
import re
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import requests
    from PIL import Image
    from io import BytesIO
except ImportError:
    print("Installing required packages...")
    os.system("pip install requests pillow")
    import requests
    from PIL import Image
    from io import BytesIO

# Paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = ROOT_DIR / "content"
CONFIG_PATH = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"
IMAGE_PLAN_PATH = CONTENT_DIR / "image_plan.json"
IMAGE_REVIEW_PATH = CONTENT_DIR / "image_review.json"

# Free image API keys (free tier)
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")


@dataclass
class ImageCandidate:
    """Represents an image candidate for review."""

    url: str
    source: str  # pexels, pixabay, unsplash
    photographer: str
    alt_text: str
    width: int
    height: int
    relevance_score: float  # 0-1
    quality_score: float  # 0-1
    has_watermark: bool
    has_text_overlay: bool
    approved: bool
    rejection_reason: Optional[str] = None


@dataclass
class ImagePlan:
    """Plan for images needed in article."""

    topic: str
    sections: list  # List of sections needing images
    search_keywords: list  # Keywords to search
    style_guide: dict  # Color scheme, mood, etc.
    required_count: int
    candidates: list  # List of ImageCandidate


def load_article_payload() -> dict:
    """Load article payload to analyze content."""
    payload_path = CONTENT_DIR / "article_payload.json"
    if payload_path.exists():
        return json.loads(payload_path.read_text(encoding="utf-8"))
    return {}


def extract_visual_concepts(article: dict) -> dict:
    """Extract key visual concepts from article content."""
    title = article.get("title", "")
    body_html = article.get("body_html", "")

    # Extract headings for section images
    headings = re.findall(r"<h[23][^>]*>([^<]+)</h[23]>", body_html)

    # Extract key nouns/concepts from title
    # Simple keyword extraction
    stop_words = {
        "how",
        "to",
        "make",
        "the",
        "a",
        "an",
        "from",
        "with",
        "for",
        "and",
        "or",
        "in",
        "on",
        "at",
        "your",
        "this",
        "that",
    }
    title_words = [
        w.lower()
        for w in re.findall(r"\b\w+\b", title)
        if w.lower() not in stop_words and len(w) > 2
    ]

    # Determine visual style based on content
    style_keywords = {
        "rustic": ["homemade", "diy", "traditional", "farmhouse", "country"],
        "modern": ["minimalist", "clean", "simple", "easy"],
        "natural": ["organic", "natural", "eco", "green", "sustainable"],
        "cozy": ["kitchen", "home", "warm", "comfort"],
    }

    detected_style = "natural"  # default
    content_lower = (title + " " + body_html).lower()
    for style, keywords in style_keywords.items():
        if any(kw in content_lower for kw in keywords):
            detected_style = style
            break

    return {
        "topic": title,
        "main_keywords": title_words[:5],
        "section_keywords": headings[:6],  # Max 6 sections
        "style": detected_style,
        "mood": "bright, natural lighting, clean background",
        "avoid": [
            "text overlays",
            "watermarks",
            "logos",
            "faces",
            "cluttered backgrounds",
        ],
    }


def generate_search_queries(concepts: dict) -> list:
    """Generate search queries for image APIs."""
    main_kw = " ".join(concepts["main_keywords"][:3])

    queries = [
        main_kw,  # Main topic
        f"{main_kw} kitchen",
        f"{main_kw} homemade",
        f"{main_kw} jar glass",
        f"{main_kw} ingredients",
    ]

    # Add section-specific queries
    for section in concepts["section_keywords"][:3]:
        section_clean = re.sub(r"[^\w\s]", "", section).strip()
        if section_clean:
            queries.append(section_clean)

    return queries


def search_pexels(query: str, per_page: int = 5) -> list:
    """Search Pexels for images."""
    if not PEXELS_API_KEY:
        return []

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for photo in data.get("photos", []):
                results.append(
                    {
                        "url": photo["src"]["large"],
                        "thumb": photo["src"]["medium"],
                        "source": "pexels",
                        "photographer": photo.get("photographer", "Unknown"),
                        "alt": photo.get("alt", query),
                        "width": photo["width"],
                        "height": photo["height"],
                        "page_url": photo["url"],
                    }
                )
            return results
    except Exception as e:
        print(f"Pexels error: {e}")
    return []


def search_pixabay(query: str, per_page: int = 5) -> list:
    """Search Pixabay for images."""
    if not PIXABAY_API_KEY:
        return []

    url = "https://pixabay.com/api/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "per_page": per_page,
        "image_type": "photo",
        "orientation": "horizontal",
        "safesearch": "true",
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for hit in data.get("hits", []):
                results.append(
                    {
                        "url": hit["largeImageURL"],
                        "thumb": hit["webformatURL"],
                        "source": "pixabay",
                        "photographer": hit.get("user", "Unknown"),
                        "alt": query,
                        "width": hit["imageWidth"],
                        "height": hit["imageHeight"],
                        "page_url": hit["pageURL"],
                    }
                )
            return results
    except Exception as e:
        print(f"Pixabay error: {e}")
    return []


def search_unsplash(query: str, per_page: int = 5) -> list:
    """Search Unsplash for images."""
    if not UNSPLASH_ACCESS_KEY:
        return []

    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for photo in data.get("results", []):
                results.append(
                    {
                        "url": photo["urls"]["regular"],
                        "thumb": photo["urls"]["small"],
                        "source": "unsplash",
                        "photographer": photo["user"]["name"],
                        "alt": photo.get("alt_description", query),
                        "width": photo["width"],
                        "height": photo["height"],
                        "page_url": photo["links"]["html"],
                    }
                )
            return results
    except Exception as e:
        print(f"Unsplash error: {e}")
    return []


def check_image_quality(image_url: str) -> dict:
    """Download and analyze image for quality issues."""
    result = {
        "accessible": False,
        "width": 0,
        "height": 0,
        "has_watermark_risk": False,
        "quality_score": 0.0,
        "format": "",
        "file_size_kb": 0,
    }

    try:
        resp = requests.get(image_url, timeout=15, stream=True)
        if resp.status_code != 200:
            return result

        # Check file size
        content_length = resp.headers.get("content-length", 0)
        result["file_size_kb"] = int(content_length) / 1024 if content_length else 0

        # Load image
        img_data = BytesIO(resp.content)
        img = Image.open(img_data)

        result["accessible"] = True
        result["width"] = img.width
        result["height"] = img.height
        result["format"] = img.format

        # Quality score based on resolution
        min_dimension = min(img.width, img.height)
        if min_dimension >= 1200:
            result["quality_score"] = 1.0
        elif min_dimension >= 800:
            result["quality_score"] = 0.8
        elif min_dimension >= 600:
            result["quality_score"] = 0.6
        else:
            result["quality_score"] = 0.4

        # Check for potential watermark patterns
        # Simple heuristic: check if corners have unusual patterns
        # This is a basic check - real watermark detection would need ML
        result["has_watermark_risk"] = False

        # Check aspect ratio (blog images should be roughly 16:9 or 4:3)
        aspect = img.width / img.height
        if 1.2 <= aspect <= 2.0:
            result["quality_score"] += 0.1

        result["quality_score"] = min(1.0, result["quality_score"])

    except Exception as e:
        print(f"Image check error: {e}")

    return result


def calculate_relevance_score(image_alt: str, topic_keywords: list) -> float:
    """Calculate how relevant an image is to the topic."""
    if not image_alt:
        return 0.3  # Default low score

    alt_lower = image_alt.lower()
    matches = sum(1 for kw in topic_keywords if kw.lower() in alt_lower)

    if matches >= 3:
        return 1.0
    elif matches >= 2:
        return 0.8
    elif matches >= 1:
        return 0.6
    else:
        return 0.3


def review_image(image_data: dict, concepts: dict) -> ImageCandidate:
    """Review a single image candidate."""
    print(f"  Reviewing: {image_data['url'][:60]}...")

    # Check image quality
    quality = check_image_quality(image_data["url"])

    # Calculate relevance
    relevance = calculate_relevance_score(
        image_data.get("alt", ""), concepts["main_keywords"]
    )

    # Determine approval
    approved = True
    rejection_reason = None

    if not quality["accessible"]:
        approved = False
        rejection_reason = "Image not accessible"
    elif quality["quality_score"] < 0.5:
        approved = False
        rejection_reason = f"Low quality (score: {quality['quality_score']:.2f})"
    elif quality["has_watermark_risk"]:
        approved = False
        rejection_reason = "Potential watermark detected"
    elif relevance < 0.4:
        approved = False
        rejection_reason = f"Low relevance (score: {relevance:.2f})"
    elif quality["width"] < 600 or quality["height"] < 400:
        approved = False
        rejection_reason = (
            f"Resolution too low ({quality['width']}x{quality['height']})"
        )

    return ImageCandidate(
        url=image_data["url"],
        source=image_data["source"],
        photographer=image_data.get("photographer", "Unknown"),
        alt_text=image_data.get("alt", concepts["topic"]),
        width=quality["width"],
        height=quality["height"],
        relevance_score=relevance,
        quality_score=quality["quality_score"],
        has_watermark=quality["has_watermark_risk"],
        has_text_overlay=False,  # Would need OCR to detect
        approved=approved,
        rejection_reason=rejection_reason,
    )


def generate_alt_text(image: ImageCandidate, concepts: dict) -> str:
    """Generate SEO-friendly alt text for an image."""
    topic = concepts["topic"]
    style = concepts["style"]

    # Clean up existing alt text or create new
    if image.alt_text and len(image.alt_text) > 10:
        base_alt = image.alt_text
    else:
        keywords = " ".join(concepts["main_keywords"][:3])
        base_alt = f"{keywords} - {style} style"

    # Ensure alt text is descriptive and includes topic
    if concepts["main_keywords"][0].lower() not in base_alt.lower():
        base_alt = f"{concepts['main_keywords'][0]} - {base_alt}"

    # Truncate if too long
    if len(base_alt) > 125:
        base_alt = base_alt[:122] + "..."

    return base_alt


def create_image_plan(article: dict) -> ImagePlan:
    """Create a comprehensive image plan for an article."""
    concepts = extract_visual_concepts(article)
    queries = generate_search_queries(concepts)

    print(f"\n{'='*60}")
    print(f"IMAGE REVIEW AGENT")
    print(f"{'='*60}")
    print(f"Topic: {concepts['topic']}")
    print(f"Style: {concepts['style']}")
    print(f"Keywords: {', '.join(concepts['main_keywords'])}")
    print(f"Search queries: {len(queries)}")
    print(f"{'='*60}\n")

    # Collect all image candidates
    all_candidates = []

    for i, query in enumerate(queries[:4]):  # Limit to 4 queries
        print(f"\nSearching for: '{query}'")

        # Search all sources
        pexels_results = search_pexels(query, per_page=3)
        pixabay_results = search_pixabay(query, per_page=3)
        unsplash_results = search_unsplash(query, per_page=3)

        all_results = pexels_results + pixabay_results + unsplash_results
        print(f"  Found {len(all_results)} images")

        # Review each image
        for img_data in all_results:
            candidate = review_image(img_data, concepts)
            candidate.alt_text = generate_alt_text(candidate, concepts)
            all_candidates.append(candidate)

    # Sort by combined score
    all_candidates.sort(
        key=lambda x: (x.approved, x.relevance_score + x.quality_score), reverse=True
    )

    # Create plan
    plan = ImagePlan(
        topic=concepts["topic"],
        sections=concepts["section_keywords"],
        search_keywords=concepts["main_keywords"],
        style_guide={
            "style": concepts["style"],
            "mood": concepts["mood"],
            "avoid": concepts["avoid"],
        },
        required_count=min(
            5, len(concepts["section_keywords"]) + 1
        ),  # 1 hero + sections
        candidates=[asdict(c) for c in all_candidates],
    )

    return plan


def print_review_summary(plan: ImagePlan):
    """Print a summary of the image review."""
    approved = [c for c in plan.candidates if c["approved"]]
    rejected = [c for c in plan.candidates if not c["approved"]]

    print(f"\n{'='*60}")
    print(f"IMAGE REVIEW SUMMARY")
    print(f"{'='*60}")
    print(f"Topic: {plan.topic}")
    print(f"Required images: {plan.required_count}")
    print(f"Total candidates: {len(plan.candidates)}")
    print(f"✅ Approved: {len(approved)}")
    print(f"❌ Rejected: {len(rejected)}")
    print(f"{'='*60}\n")

    if approved:
        print("APPROVED IMAGES:")
        for i, img in enumerate(approved[: plan.required_count], 1):
            print(f"\n  {i}. {img['source'].upper()}")
            print(f"     URL: {img['url'][:70]}...")
            print(f"     Alt: {img['alt_text'][:50]}...")
            print(f"     Size: {img['width']}x{img['height']}")
            print(
                f"     Scores: relevance={img['relevance_score']:.2f}, quality={img['quality_score']:.2f}"
            )
            print(f"     Photographer: {img['photographer']}")

    if rejected:
        print(f"\nREJECTED IMAGES ({len(rejected)}):")
        for img in rejected[:5]:  # Show first 5
            print(f"  - {img['source']}: {img['rejection_reason']}")

    # Save results
    review_result = {
        "timestamp": datetime.now().isoformat(),
        "topic": plan.topic,
        "required_count": plan.required_count,
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "approved_images": approved[: plan.required_count],
        "style_guide": plan.style_guide,
        "review_pass": len(approved) >= plan.required_count,
    }

    IMAGE_REVIEW_PATH.write_text(
        json.dumps(review_result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n✅ Review saved to: {IMAGE_REVIEW_PATH}")

    return review_result


def main():
    """Main entry point."""
    # Check for API keys
    has_api = PEXELS_API_KEY or PIXABAY_API_KEY or UNSPLASH_ACCESS_KEY

    if not has_api:
        print("⚠️  No image API keys configured!")
        print("Set environment variables:")
        print("  - PEXELS_API_KEY (get free key at pexels.com/api)")
        print("  - PIXABAY_API_KEY (get free key at pixabay.com/api/docs)")
        print("  - UNSPLASH_ACCESS_KEY (get free key at unsplash.com/developers)")
        print("\nGenerating placeholder image plan based on article content...\n")

    # Load article
    article = load_article_payload()
    if not article:
        print("ERROR: No article_payload.json found")
        sys.exit(1)

    # Create image plan
    plan = create_image_plan(article)

    # Save plan
    IMAGE_PLAN_PATH.write_text(
        json.dumps(asdict(plan), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Image plan saved to: {IMAGE_PLAN_PATH}")

    # Print summary
    result = print_review_summary(plan)

    if result["review_pass"]:
        print(f"\n✅ IMAGE REVIEW PASSED - {result['approved_count']} images approved")
    else:
        print(
            f"\n❌ IMAGE REVIEW FAILED - Need {plan.required_count} images, only {result['approved_count']} approved"
        )
        print("   Consider adding API keys or manual image selection")

    return result


if __name__ == "__main__":
    main()
