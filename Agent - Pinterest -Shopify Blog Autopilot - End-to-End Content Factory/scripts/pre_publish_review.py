#!/usr/bin/env python3
"""
PRE-PUBLISH REVIEW CHECKLIST
Run this BEFORE publishing any article to ensure META-PROMPT compliance.

This script must pass ALL checks before any content goes live.
"""

import json
import os
import re
import sys
import io
from pathlib import Path

import requests
try:
    from PIL import Image, ImageStat  # type: ignore
except Exception:
    Image = None
    ImageStat = None

# Fix encoding for Windows console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).parent.parent
CONFIG_PATH = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


config = load_config()
shop_config = config.get("shop", {})

SHOP = os.environ.get(
    "SHOPIFY_STORE_DOMAIN",
    os.environ.get("SHOPIFY_SHOP", shop_config.get("domain", "")),
)
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get(
    "SHOPIFY_TOKEN", shop_config.get("access_token", "")
)
BLOG_ID = os.environ.get(
    "SHOPIFY_BLOG_ID",
    os.environ.get("BLOG_ID", shop_config.get("blog_id", "")),
)
API_VERSION = os.environ.get(
    "SHOPIFY_API_VERSION", shop_config.get("api_version", "2025-01")
)

if not SHOP or not TOKEN or not BLOG_ID:
    raise SystemExit(
        "Missing Shopify config. Set SHOPIFY_STORE_DOMAIN, SHOPIFY_ACCESS_TOKEN, and SHOPIFY_BLOG_ID."
    )

HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# META-PROMPT REQUIREMENTS
REQUIREMENTS = {
    "min_words": 1800,
    "max_words": 2200,
    "min_figures": 3,
    "min_blockquotes": 2,
    "min_tables": 1,
    "main_image_required": True,
    "main_image_alt_required": True,
    "inline_images_min": 3,
    "inline_image_alt_required": True,
}

# REQUIRED FIELDS - Must not be empty
REQUIRED_FIELDS = [
    "title",
    "body_html",
    "handle",
]

# RECOMMENDED FIELDS - Should not be empty for SEO
RECOMMENDED_FIELDS = [
    "meta_description",  # SEO meta description (summary_html fallback)
    "author",  # Author name
    "tags",  # Tags for categorization
]

# SEO REQUIREMENTS
SEO_REQUIREMENTS = {
    "title_min_length": 30,
    "title_max_length": 60,
    "meta_desc_min_length": 50,
    "meta_desc_max_length": 160,
    "min_internal_links": 2,  # Links to other blog posts
    "min_headings": 5,  # H2/H3 headings for structure
    "min_lists": 2,  # <ul> or <ol> for scanability
}

# CONTENT QUALITY CHECKS
QUALITY_CHECKS = {
    "check_broken_images": True,
    "check_duplicate_images": True,
    "check_empty_paragraphs": True,
    "check_heading_hierarchy": True,  # H2 before H3
    "check_call_to_action": True,  # CTA in content
    "check_intro_paragraph": True,  # First paragraph should be engaging
}

# META-PROMPT HARD VALIDATIONS (from SHOPIFY BLOG META-PROMPT)
META_PROMPT_CHECKS = {
    "strict_no_years": True,  # Ban \b(19|20)\d{2}\b in all fields
    "min_sources_links": 5,  # ≥5 citations in Sources section
    "min_expert_quotes": 2,  # ≥2 expert quotes with real name/title/org
    "min_stats": 3,  # ≥3 quantified stats with sources
    "require_kebab_ids": True,  # All H2/H3 must have kebab-case id
    "require_rel_nofollow": True,  # All links need rel="nofollow noopener"
    "no_schema_in_body": True,  # Schema JSON-LD NOT inside body HTML
    "require_direct_answer": True,  # Opening paragraph 50-70 words
    "require_key_terms": True,  # Key Terms section required
    "require_sources_section": True,  # Sources & Further Reading section
}

# 11-section structure (pattern-based, case-insensitive)
REQUIRED_SECTION_PATTERNS = [
    ("Direct Answer", r"\bdirect answer\b"),
    ("Key Conditions", r"\bkey conditions\b"),
    ("Understanding", r"\bunderstanding\b"),
    ("Step-by-Step", r"\bstep[-\s]?by[-\s]?step\b"),
    ("Types/Varieties", r"\btypes\b|\bvarieties\b"),
    ("Troubleshooting", r"\btroubleshooting\b|\bcommon issues\b"),
    ("Pro Tips/Experts", r"\bpro tips\b|\bexperts?\b"),
    ("FAQs", r"\bfaq\b|\bfrequently asked\b"),
    ("Advanced Techniques", r"\badvanced\b"),
    ("Comparison Table", r"\bcomparison\b|\btable\b"),
    ("Sources", r"\bsources?\b|\bfurther reading\b|\breferences\b"),
]

# Generic phrases to block
GENERIC_PHRASES = [
    "this comprehensive guide provides",
    "this comprehensive guide covers",
    "this practical guide",
    "whether you are a beginner",
    "whether you're a beginner",
    "professional practitioners recommend",
    "achieving consistent results requires",
    "once you've perfected small batches",
    "scaling up becomes appealing",
    "making larger batches requires",
    "heat distribution",
    "doubling recipes",
    "measuring cups",
    "dry ingredients",
    "wet ingredients",
    "shelf life 2-4 weeks",
    "shelf life 3-6 months",
    "in conclusion",
    "in summary",
    "overall,",
    "this article",
    "this blog post",
    "as we have seen",
    "keep in mind",
    "with the right approach",
    "it's important to remember",
    "it is important to remember",
    "on the other hand",
    "at the end of the day",
    "this guide explains",
    "you will learn what works",
    "by the end, you will know",
    "taking your understanding to the next level",
    "no one succeeds in isolation",
    "in today's fast-paced world",
    "perfect for anyone looking to improve",
    "join thousands who have already mastered",
    "here's everything you need to know",
    "here is everything you need to know",
    "we'll walk you through",
    "we will walk you through",
    "let's dive in",
    "in this post we'll",
    "in this post we will",
    "in this article we'll",
    "in this article we will",
    "read on to learn",
    "read on to discover",
    "without further ado",
    "when it comes to",
    "the bottom line is",
    "it goes without saying",
    "needless to say",
    "first and foremost",
    "last but not least",
    "when all is said and done",
    "one of the best ways",
    "one of the most important",
    "there are many ways to",
    "there are a number of",
    "it's worth noting",
    "it is worth noting",
    "as mentioned above",
    "as stated earlier",
    "more often than not",
    "at the end of the day",
    "when it comes down to it",
    # AI slop / generic filler (2024-2025)
    "delve into",
    "dive deep",
    "dive deeper",
    "navigate the landscape",
    "tapestry of",
    "realm of possibilities",
    "in the realm of",
    "as we continue to evolve",
    "i'm excited to announce",
    "thrilled to share",
    "it's essential to",
    "it is essential to",
    "crucial to understand",
    "game-changer",
    "unlock the potential",
    "master the art of",
    "elevate your",
    "transform your",
    "navigating the world of",
    "empower yourself",
    "unlock the secrets",
    "discover the power of",
    "harness the power",
    "key takeaways",
    "in a nutshell",
    "at its core",
    "boils down to",
    "in essence",
    "the truth is",
    "the reality is",
    "simply put",
    "to put it simply",
    "taking it to the next level",
    "stay ahead of the curve",
    "stay ahead of the game",
    "proven strategies",
    "tried and tested",
    "get started today",
    "start your journey",
    "embark on",
    "dive right in",
    "let's explore",
    "in this comprehensive",
    "this in-depth",
    "deep dive into",
    "comprehensive breakdown",
    "ultimate guide to",
    "synergy",
    "leverage the power",
    "thought leadership",
    "industry-leading",
    "world-class",
    "best-in-class",
    "gold standard",
    "silver bullet",
    "no-brainer",
    "must-have",
]

GENERIC_SECTION_HEADINGS = [
    "advanced considerations and expert insights",
    "timing and seasonal factors",
    "quality over quantity",
    "building community connections",
    "continuous learning mindset",
    "environmental responsibility",
    "documentation and reflection",
    "practical tips",
    "maintenance and care",
    "research highlights",
    "expert insights",
]

ALLOWED_IMAGE_SOURCES = ["cdn.shopify.com", "i.pinimg.com"]
DISALLOWED_IMAGE_SOURCES = ["pollinations.ai", "pexels.com"]

# Regex patterns
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
KEBAB_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STAT_MARKER_PATTERN = re.compile(r"\[EVID:STAT_\d+\]")
QUOTE_MARKER_PATTERN = re.compile(r"\[EVID:QUOTE_\d+\]")
STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "for",
    "to",
    "with",
    "in",
    "on",
    "at",
    "by",
    "from",
    "as",
    "is",
    "are",
    "be",
    "your",
    "you",
    "our",
    "we",
    "this",
    "that",
    "these",
    "those",
    "how",
    "guide",
    "complete",
    "step",
    "steps",
    "easy",
    "budget",
    "friendly",
}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def _extract_section_text(body_html: str, heading_pattern: str) -> str:
    if not body_html:
        return ""
    heading = re.search(
        rf"<h2[^>]*>.*?{heading_pattern}.*?</h2>",
        body_html,
        re.IGNORECASE | re.DOTALL,
    )
    if not heading:
        return ""
    start = heading.end()
    next_h2 = re.search(r"<h2[^>]*>", body_html[start:], re.IGNORECASE)
    chunk = body_html[start : start + next_h2.start()] if next_h2 else body_html[start:]
    return _strip_html(chunk)


def _extract_last_paragraphs(body_html: str, count: int = 2) -> str:
    paras = re.findall(r"<p[^>]*>(.*?)</p>", body_html, re.IGNORECASE | re.DOTALL)
    cleaned = [_strip_html(p).strip() for p in paras if _strip_html(p).strip()]
    if not cleaned:
        return ""
    return " ".join(cleaned[-count:])


def _topic_keywords(title: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", (title or "").lower())
    keep = [t for t in tokens if t not in STOPWORDS and (len(t) >= 3)]
    return list(dict.fromkeys(keep))


def _contains_topic(text: str, keywords: list[str]) -> bool:
    if not text or not keywords:
        return True
    text_lower = _strip_html(text).lower()
    return any(kw in text_lower for kw in keywords)


def validate_image_url(url: str, timeout: int = 10) -> tuple:
    """
    Validate that an image URL is accessible.
    Returns (is_valid, status_code_or_error)
    """
    if not url:
        return False, "NO_URL"
    try:
        # Use GET request (Pexels and most CDNs work with GET)
        resp = requests.get(url, timeout=timeout, stream=True)
        resp.close()  # Don't download entire image
        return resp.status_code == 200, resp.status_code
    except requests.Timeout:
        return False, "TIMEOUT"
    except requests.ConnectionError:
        return False, "CONNECTION_ERROR"
    except Exception as e:
        return False, str(e)[:30]


def _is_blank_image(image_bytes: bytes) -> bool:
    """
    Best-effort blank/near-blank detection.
    Uses Pillow when available; otherwise returns False.
    """
    if Image is None or ImageStat is None:
        return False
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("L").resize((64, 64))
        stat = ImageStat.Stat(img)
        mean = stat.mean[0]
        var = stat.var[0]
        if (mean >= 245 or mean <= 10) and var < 15:
            return True
    except Exception:
        return False
    return False


def review_article(article_id):
    """Comprehensive review of a single article"""
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code != 200:
        return {"passed": False, "errors": ["Failed to fetch article"]}

    article = resp.json()["article"]
    body = article.get("body_html", "")
    title = article.get("title", "Unknown")

    errors = []
    warnings = []
    empty_fields = []

    # ========== EMPTY FIELD CHECKS ==========
    # Required fields - must not be empty
    for field in REQUIRED_FIELDS:
        value = article.get(field, "")
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(f"❌ EMPTY FIELD: '{field}' is required but empty")
            empty_fields.append(field)

    # Recommended fields - should not be empty for SEO
    for field in RECOMMENDED_FIELDS:
        value = article.get(field, "")
        if field == "tags":
            # Tags is a string like "tag1, tag2"
            if not value or (isinstance(value, str) and not value.strip()):
                warnings.append(
                    f"⚠️ EMPTY FIELD: '{field}' recommended for SEO/categorization"
                )
                empty_fields.append(field)
        elif field == "meta_description":
            # Check summary_html as fallback for meta description
            summary = article.get("summary_html", "")
            if (not value or not value.strip()) and (
                not summary or not summary.strip()
            ):
                errors.append(
                    f"❌ META DESCRIPTION: Missing meta_description and summary_html"
                )
                empty_fields.append(field)
            elif value and len(value) > 160:
                errors.append(
                    f"❌ META DESCRIPTION: {len(value)} chars > 160 required max"
                )
            elif value and len(value) < 50:
                errors.append(
                    f"❌ META DESCRIPTION: {len(value)} chars < 50 required min"
                )
        else:
            if not value or (isinstance(value, str) and not value.strip()):
                warnings.append(f"⚠️ EMPTY FIELD: '{field}' recommended")
                empty_fields.append(field)

    # 1. Word count check
    word_count = len(body.split())
    if word_count < REQUIREMENTS["min_words"]:
        errors.append(f"❌ WORDS: {word_count} < {REQUIREMENTS['min_words']} minimum")
    elif word_count > REQUIREMENTS["max_words"]:
        warnings.append(
            f"⚠️ WORDS: {word_count} > {REQUIREMENTS['max_words']} (slightly over)"
        )

    # 1b. Generic content check (strict - block AI slop before publish)
    text_lower = re.sub(r"<[^>]+>", " ", body).lower()
    found_generic = [phrase for phrase in GENERIC_PHRASES if phrase in text_lower]
    if found_generic:
        # Show first 5 for debugging, all count toward fail
        errors.append(
            f"❌ GENERIC CONTENT (agent must fix): {', '.join(found_generic[:5])}"
            + (f" (+{len(found_generic)-5} more)" if len(found_generic) > 5 else "")
        )
    if GENERIC_SECTION_HEADINGS:
        heading_hits = []
        for heading in GENERIC_SECTION_HEADINGS:
            if re.search(
                rf"<h[2-3][^>]*>\s*{re.escape(heading)}\s*</h[2-3]>",
                body,
                re.IGNORECASE,
            ):
                heading_hits.append(heading)
        if heading_hits:
            errors.append(f"❌ GENERIC HEADINGS: {', '.join(heading_hits[:3])}")

    # 1c. Topic drift checks (intro + ending must mention title keywords)
    topic_keys = _topic_keywords(title)
    direct_text = _extract_section_text(body, "direct answer")
    if not direct_text:
        # fallback to first paragraph
        first_p = re.search(r"<p[^>]*>(.+?)</p>", body, re.IGNORECASE | re.DOTALL)
        direct_text = _strip_html(first_p.group(1)) if first_p else ""
    if topic_keys and not _contains_topic(direct_text, topic_keys):
        errors.append(
            f"❌ TOPIC DRIFT: Direct Answer does not mention topic keywords ({', '.join(topic_keys[:3])})"
        )

    tail_text = _extract_last_paragraphs(body, count=2)
    if topic_keys and tail_text and not _contains_topic(tail_text, topic_keys):
        errors.append(
            f"❌ TOPIC DRIFT: Ending paragraphs do not mention topic keywords ({', '.join(topic_keys[:3])})"
        )

    # 2. Main image check
    main_image = article.get("image")
    all_image_urls = []  # Collect all image URLs for validation

    if REQUIREMENTS["main_image_required"]:
        if not main_image:
            errors.append("❌ MAIN IMAGE: Missing featured/thumbnail image")
        else:
            main_alt = main_image.get("alt", "")
            if REQUIREMENTS["main_image_alt_required"] and not main_alt:
                errors.append("❌ MAIN IMAGE ALT: Missing alt text for main image")

            # Check if image URL is valid
            main_src = main_image.get("src", "")
            if not main_src:
                errors.append("❌ MAIN IMAGE SRC: No image URL")
            else:
                all_image_urls.append(("MAIN", main_src))

    # 3. Inline images check
    img_tags = re.findall(r"<img[^>]+>", body, re.IGNORECASE)
    if len(img_tags) < REQUIREMENTS["inline_images_min"]:
        errors.append(
            f"❌ INLINE IMAGES: {len(img_tags)} < {REQUIREMENTS['inline_images_min']} required"
        )

    # Check inline image alt texts
    for i, tag in enumerate(img_tags, 1):
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', tag)
        if REQUIREMENTS["inline_image_alt_required"]:
            if not alt_match or not alt_match.group(1).strip():
                errors.append(f"❌ INLINE IMAGE {i} ALT: Missing alt text")

        # Check if src exists
        src_match = re.search(r'src=["\']([^"\']+)["\']', tag)
        if not src_match:
            errors.append(f"❌ INLINE IMAGE {i} SRC: Missing src URL")
        else:
            all_image_urls.append((f"INLINE_{i}", src_match.group(1)))

    # 3.5. IMAGE URL VALIDATION - Check all image URLs are accessible
    broken_images = []
    blank_images = []
    for img_name, img_url in all_image_urls:
        is_valid, status = validate_image_url(img_url)
        if not is_valid:
            broken_images.append((img_name, status, img_url[:60]))
        else:
            try:
                resp = requests.get(img_url, timeout=10)
                if resp.status_code == 200:
                    content = resp.content
                    if len(content) < 8192:
                        blank_images.append((img_name, "TOO_SMALL", img_url[:60]))
                    elif _is_blank_image(content):
                        blank_images.append((img_name, "BLANK", img_url[:60]))
            except Exception:
                pass

        if any(src in img_url for src in DISALLOWED_IMAGE_SOURCES):
            errors.append(f"❌ DISALLOWED IMAGE SOURCE: {img_name} uses {img_url[:60]}...")
        if not any(src in img_url for src in ALLOWED_IMAGE_SOURCES):
            errors.append(f"❌ IMAGE SOURCE NOT ALLOWED: {img_name} uses {img_url[:60]}...")

    if broken_images:
        for img_name, status, url_preview in broken_images:
            errors.append(
                f"❌ BROKEN IMAGE ({img_name}): HTTP {status} - {url_preview}..."
            )
        errors.append(
            f"❌ IMAGE VALIDATION: {len(broken_images)}/{len(all_image_urls)} images not accessible"
        )
    if blank_images:
        for img_name, status, url_preview in blank_images:
            errors.append(
                f"❌ BLANK IMAGE ({img_name}): {status} - {url_preview}..."
            )
        errors.append(
            f"❌ BLANK IMAGES: {len(blank_images)}/{len(all_image_urls)} appear blank or too small"
        )

    # 4. Figure tags check (proper image formatting)
    figure_count = body.count("<figure")
    if figure_count < REQUIREMENTS["min_figures"]:
        errors.append(
            f"❌ FIGURES: {figure_count} < {REQUIREMENTS['min_figures']} required (use <figure> tags)"
        )

    # 5. Blockquotes check (expert quotes)
    blockquote_count = body.count("<blockquote")
    if blockquote_count < REQUIREMENTS["min_blockquotes"]:
        errors.append(
            f"❌ BLOCKQUOTES: {blockquote_count} < {REQUIREMENTS['min_blockquotes']} required (expert quotes)"
        )

    # 6. Tables check
    table_count = body.count("<table")
    if table_count < REQUIREMENTS["min_tables"]:
        errors.append(
            f"❌ TABLES: {table_count} < {REQUIREMENTS['min_tables']} required"
        )

    # 6b. Check tables are mobile responsive
    if table_count > 0:
        # Check if tables are wrapped in responsive container
        responsive_tables = (
            body.count('class="table-responsive"')
            + body.count("overflow-x: auto")
            + body.count("overflow-x:auto")
        )
        if responsive_tables < table_count:
            warnings.append(
                f"⚠️ TABLES NOT MOBILE RESPONSIVE: {table_count} tables but only {responsive_tables} wrapped in responsive container. "
                'Wrap tables in <div style="overflow-x: auto;"> for mobile compatibility.'
            )

    # ========== SEO CHECKS ==========
    # 7. Title length check
    title_length = len(title)
    if title_length < SEO_REQUIREMENTS["title_min_length"]:
        warnings.append(
            f"⚠️ TITLE LENGTH: {title_length} < {SEO_REQUIREMENTS['title_min_length']} chars (too short for SEO)"
        )
    elif title_length > SEO_REQUIREMENTS["title_max_length"]:
        warnings.append(
            f"⚠️ TITLE LENGTH: {title_length} > {SEO_REQUIREMENTS['title_max_length']} chars (may truncate in SERP)"
        )

    # 8. Heading structure check (H2, H3)
    h2_count = len(re.findall(r"<h2[^>]*>", body, re.IGNORECASE))
    h3_count = len(re.findall(r"<h3[^>]*>", body, re.IGNORECASE))
    total_headings = h2_count + h3_count
    if total_headings < SEO_REQUIREMENTS["min_headings"]:
        errors.append(
            f"❌ HEADINGS: {total_headings} < {SEO_REQUIREMENTS['min_headings']} (need more H2/H3 for structure)"
        )

    # 9. Lists check (ul/ol for scanability)
    ul_count = body.count("<ul")
    ol_count = body.count("<ol")
    total_lists = ul_count + ol_count
    if total_lists < SEO_REQUIREMENTS["min_lists"]:
        errors.append(
            f"❌ LISTS: {total_lists} < {SEO_REQUIREMENTS['min_lists']} (add bullet/numbered lists)"
        )

    # 10. Internal links check
    internal_links = len(
        re.findall(
            r'href=["\'][^"\']*(?:the-rike|/blogs/)[^"\']*["\']', body, re.IGNORECASE
        )
    )
    if internal_links < SEO_REQUIREMENTS["min_internal_links"]:
        warnings.append(
            f"⚠️ INTERNAL LINKS: {internal_links} < {SEO_REQUIREMENTS['min_internal_links']} (add links to other blog posts)"
        )

    # ========== QUALITY CHECKS ==========
    # 11. Empty paragraphs check
    if QUALITY_CHECKS["check_empty_paragraphs"]:
        empty_p = len(re.findall(r"<p[^>]*>\s*</p>", body, re.IGNORECASE))
        if empty_p > 0:
            warnings.append(
                f"⚠️ EMPTY PARAGRAPHS: {empty_p} found (remove or add content)"
            )

    # 12. Duplicate images check
    img_srcs = []
    unique_srcs = set()
    if QUALITY_CHECKS["check_duplicate_images"]:
        img_srcs = re.findall(
            r'<img[^>]+src=["\']([^"\']+)["\']', body, re.IGNORECASE
        )
        unique_srcs = set(img_srcs)
        if len(img_srcs) != len(unique_srcs):
            errors.append(
                f"❌ DUPLICATE IMAGES: {len(img_srcs) - len(unique_srcs)} duplicate image(s) found"
            )

    # 13. Heading hierarchy check (H2 should come before H3)
    if QUALITY_CHECKS["check_heading_hierarchy"]:
        first_h2 = body.find("<h2")
        first_h3 = body.find("<h3")
        if first_h3 != -1 and (first_h2 == -1 or first_h3 < first_h2):
            warnings.append(
                "⚠️ HEADING HIERARCHY: H3 appears before H2 (fix heading order)"
            )

    # 14. Call to action check
    if QUALITY_CHECKS["check_call_to_action"]:
        cta_patterns = [
            r"shop now",
            r"buy now",
            r"get started",
            r"learn more",
            r"try it",
            r"order now",
            r"add to cart",
            r"subscribe",
            r"sign up",
            r"download",
            r"check out",
            r"explore",
            r"discover",
            r"start today",
        ]
        has_cta = any(
            re.search(pattern, body, re.IGNORECASE) for pattern in cta_patterns
        )
        if not has_cta:
            warnings.append(
                "⚠️ CALL TO ACTION: No CTA found (add 'shop now', 'learn more', etc.)"
            )

    # 15. Intro paragraph quality check
    if QUALITY_CHECKS["check_intro_paragraph"]:
        first_p = re.search(r"<p[^>]*>(.+?)</p>", body, re.IGNORECASE | re.DOTALL)
        if first_p:
            intro_text = re.sub(r"<[^>]+>", "", first_p.group(1))
            intro_words = len(intro_text.split())
            if intro_words < 20:
                warnings.append(
                    f"⚠️ INTRO PARAGRAPH: Only {intro_words} words (should be 20+ for engagement)"
                )

    # 16. Image relevance check (alt texts must mention title topic) — ERROR if fail
    topic_keys = _topic_keywords(title)
    all_alts = []
    if main_image and main_image.get("alt"):
        all_alts.append(main_image.get("alt").lower())
    for tag in img_tags:
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', tag)
        if alt_match:
            all_alts.append(alt_match.group(1).lower())

    topic_mentioned = False
    if topic_keys:
        for alt in all_alts:
            if any(kw in alt for kw in topic_keys):
                topic_mentioned = True
                break
        if not topic_mentioned:
            errors.append(
                f"❌ IMAGE RELEVANCE: Alt texts must mention topic keywords from title ({', '.join(topic_keys[:5])})"
            )

    # 16a. Prefer Pinterest images when available (not required)
    all_srcs = []
    if main_image and main_image.get("src"):
        all_srcs.append(main_image.get("src"))
    for tag in img_tags:
        src_match = re.search(r'src=["\']([^"\']+)["\']', tag)
        if src_match:
            all_srcs.append(src_match.group(1))
    has_pinterest = any("i.pinimg.com" in (s or "") for s in all_srcs)
    if not has_pinterest and all_srcs:
        warnings.append(
            "⚠️ IMAGE QUALITY: No Pinterest image detected; using AI/Shopify images"
        )

    # 16b. Required section structure check (H2/H3 text)
    heading_texts = re.findall(
        r"<h[23][^>]*>(.*?)</h[23]>",
        body,
        re.IGNORECASE | re.DOTALL,
    )
    heading_texts = [
        re.sub(r"<[^>]+>", " ", h).replace("&amp;", "&").strip().lower()
        for h in heading_texts
    ]
    missing_sections = []
    for label, pattern in REQUIRED_SECTION_PATTERNS:
        if not any(re.search(pattern, h, re.IGNORECASE) for h in heading_texts):
            missing_sections.append(label)
    if missing_sections:
        errors.append(
            f"❌ SECTION STRUCTURE: Missing required sections: {', '.join(missing_sections)}"
        )

    # 16b. Required section structure check (H2/H3 text)
    heading_texts = re.findall(
        r"<h[23][^>]*>(.*?)</h[23]>",
        body,
        re.IGNORECASE | re.DOTALL,
    )
    heading_texts = [
        re.sub(r"<[^>]+>", " ", h).replace("&amp;", "&").strip().lower()
        for h in heading_texts
    ]
    missing_sections = []
    for label, pattern in REQUIRED_SECTION_PATTERNS:
        if not any(re.search(pattern, h, re.IGNORECASE) for h in heading_texts):
            missing_sections.append(label)
    if missing_sections:
        errors.append(
            f"❌ SECTION STRUCTURE: Missing required sections: {', '.join(missing_sections)}"
        )

    # ========== META-PROMPT HARD VALIDATIONS ==========
    # Initialize tracking variables
    sources_links_count = 0
    sources_section_urls = []
    valid_quotes = 0
    stats_found = 0
    headings_with_id = []
    headings_without_id = 0

    # 17. STRICT NO YEARS check - ban \b(19|20)\d{2}\b in all fields
    if META_PROMPT_CHECKS["strict_no_years"]:
        # Check title, body, alt texts
        year_in_title = YEAR_PATTERN.search(title)
        year_in_body = YEAR_PATTERN.search(body)
        if year_in_title:
            errors.append(f"❌ NO YEARS: Found year '{year_in_title.group()}' in title")
        if year_in_body:
            errors.append(
                f"❌ NO YEARS: Found year(s) in body content"
            )

    # 18. Sources section check - ≥5 citations with proper links
    if META_PROMPT_CHECKS["require_sources_section"]:
        # Try finding by id containing "sources"
        sources_section = re.search(
            r'<h2[^>]*id=["\'][^"\']*sources[^"\']*["\'][^>]*>', body, re.IGNORECASE
        )
        if not sources_section:
            # Try finding by text (including HTML entities)
            sources_section = re.search(
                r"<h2[^>]*>.*(?:Sources|Further Reading|References|&amp;).*</h2>",
                body,
                re.IGNORECASE,
            )

        if not sources_section:
            errors.append(
                "❌ SOURCES SECTION: Missing Sources & Further Reading section"
            )
            sources_links_count = 0
        else:
            # Count links in sources section (after the h2)
            sources_pos = sources_section.end()
            sources_content = body[sources_pos:]
            # Stop at next h2
            next_h2 = re.search(r"<h2", sources_content, re.IGNORECASE)
            if next_h2:
                sources_content = sources_content[: next_h2.start()]
            sources_links = re.findall(
                r'<a[^>]+href=["\']https?://[^"\']+["\'][^>]*>.*?</a>',
                sources_content,
                re.IGNORECASE | re.DOTALL,
            )
            sources_section_urls = re.findall(
                r'href=["\'](https?://[^"\']+)["\']',
                sources_content,
                re.IGNORECASE,
            )
            sources_links_count = len(sources_links)

            if sources_links_count < META_PROMPT_CHECKS["min_sources_links"]:
                errors.append(
                    f"❌ SOURCES: {sources_links_count} < {META_PROMPT_CHECKS['min_sources_links']} citations required"
                )
            if sources_links:
                bad_format = []
                for link_html in sources_links:
                    text_match = re.search(
                        r'>\s*(.*?)\s*</a>',
                        link_html,
                        re.IGNORECASE | re.DOTALL,
                    )
                    raw_text = text_match.group(1) if text_match else ""
                    clean_text = re.sub(r"<[^>]+>", " ", raw_text)
                    clean_text = (
                        clean_text.replace("&mdash;", "—")
                        .replace("&#8212;", "—")
                        .strip()
                    )
                    if "—" not in clean_text:
                        bad_format.append(clean_text[:40] or "EMPTY_TEXT")
                        continue
                    if re.search(r"https?://|www\.|\.com|\.org|\.net|\.io|\.co|\.ai|\.gov|\.edu|\.vn", clean_text, re.IGNORECASE):
                        bad_format.append(clean_text[:40])
                if bad_format:
                    errors.append(
                        f"❌ SOURCES FORMAT: Links must be 'Name — Description' without raw URLs"
                    )

    # 19. Expert quotes check - ≥2 with real name/title/org
    if META_PROMPT_CHECKS["min_expert_quotes"] > 0:
        blockquotes = re.findall(
            r"<blockquote[^>]*>(.*?)</blockquote>", body, re.IGNORECASE | re.DOTALL
        )
        valid_quotes = 0
        for bq in blockquotes:
            # Check for pattern: "Quote" — Name, Title, Org  OR  <cite>— Dr. Name
            # Pattern matches: "— Dr. Name", "— Name Title", "— First Last"
            if re.search(r"[—–-]\s*(?:Dr\.?\s+)?[A-Z][a-z]+", bq):  # Has name pattern
                valid_quotes += 1

        if valid_quotes < META_PROMPT_CHECKS["min_expert_quotes"]:
            errors.append(
                f"❌ EXPERT QUOTES: {valid_quotes} < {META_PROMPT_CHECKS['min_expert_quotes']} quotes with real name/title/org"
            )

    # 20. Stats check - ≥3 quantified stats
    if META_PROMPT_CHECKS["min_stats"] > 0:
        # Look for numeric patterns with units/percentages
        stat_patterns = [
            r"\d+(?:\.\d+)?%",  # Percentages
            r"\d+(?:,\d{3})+",  # Large numbers with commas
            r"\d+(?:\.\d+)?\s*(?:ml|g|oz|lb|kg|cm|inch|hours?|minutes?|days?|weeks?|months?|years?)",  # Measurements
        ]
        stats_found = 0
        for pattern in stat_patterns:
            stats_found += len(re.findall(pattern, body, re.IGNORECASE))

        if stats_found < META_PROMPT_CHECKS["min_stats"]:
            errors.append(
                f"❌ STATS: {stats_found} < {META_PROMPT_CHECKS['min_stats']} quantified stats found"
            )

    # 21. Kebab-case IDs on H2/H3 check
    if META_PROMPT_CHECKS["require_kebab_ids"]:
        headings_with_id = re.findall(
            r'<h[23][^>]*id=["\']([^"\']+)["\']', body, re.IGNORECASE
        )
        headings_without_id = len(
            re.findall(r"<h[23](?![^>]*id=)[^>]*>", body, re.IGNORECASE)
        )

        invalid_ids = [h for h in headings_with_id if not KEBAB_PATTERN.match(h)]

        if headings_without_id > 0:
            errors.append(
                f"❌ HEADING IDS: {headings_without_id} H2/H3 tags missing id attribute"
            )
        if invalid_ids:
            errors.append(
                f"❌ HEADING IDS: Non-kebab-case ids found: {', '.join(invalid_ids[:3])}"
            )

    # 22. Links rel="nofollow noopener" check
    if META_PROMPT_CHECKS["require_rel_nofollow"]:
        all_links = re.findall(
            r'<a[^>]+href=["\'][^"\']+["\'][^>]*>',
            body,
            re.IGNORECASE,
        )
        links_without_rel = 0
        for link in all_links:
            link_lower = link.lower()
            if "rel=" not in link_lower or "nofollow" not in link_lower or "noopener" not in link_lower:
                links_without_rel += 1

        if links_without_rel > 0:
            errors.append(
                f"❌ LINK REL: {links_without_rel} links missing rel='nofollow noopener'"
            )

    # 23. No schema in body check
    if META_PROMPT_CHECKS["no_schema_in_body"]:
        if "application/ld+json" in body.lower() or '"@context"' in body:
            errors.append(
                "❌ SCHEMA IN BODY: JSON-LD schema found inside body_html (should be in metafield)"
            )

    # 24. Direct Answer opening check (50-70 words in first paragraph)
    if META_PROMPT_CHECKS["require_direct_answer"]:
        first_p = re.search(r"<p[^>]*>(.+?)</p>", body, re.IGNORECASE | re.DOTALL)
        if first_p:
            intro_text = re.sub(r"<[^>]+>", "", first_p.group(1))
            intro_words = len(intro_text.split())
            if intro_words < 50:
                errors.append(
                    f"❌ DIRECT ANSWER: Opening paragraph only {intro_words} words (need 50-70)"
                )
            elif intro_words > 70:
                errors.append(
                    f"❌ DIRECT ANSWER: Opening paragraph {intro_words} words (need 50-70)"
                )

    # 25. Key Terms section check
    if META_PROMPT_CHECKS["require_key_terms"]:
        key_terms_section = re.search(
            r"<h2[^>]*>.*Key Terms.*</h2>", body, re.IGNORECASE
        )
        if not key_terms_section:
            key_terms_section = re.search(
                r'id=["\']key-terms["\']', body, re.IGNORECASE
            )
        if not key_terms_section:
            errors.append("❌ KEY TERMS: Missing Key Terms section")

    # Summary
    passed = len(errors) == 0

    # Extract additional field values for display
    meta_desc = article.get("meta_description", "")
    summary_html = article.get("summary_html", "")
    # Fallback: use summary_html stripped of tags if meta_description is empty
    if not meta_desc and summary_html:
        meta_desc = re.sub(r"<[^>]+>", "", summary_html).strip()
    author = article.get("author", "")
    tags = article.get("tags", "")
    handle = article.get("handle", "")
    published_at = article.get("published_at", "")

    # Count responsive tables
    responsive_tables = (
        body.count('class="table-responsive"')
        + body.count("overflow-x: auto")
        + body.count("overflow-x:auto")
    )

    return {
        "article_id": article_id,
        "title": title,
        "passed": passed,
        "word_count": word_count,
        "main_image": bool(main_image),
        "main_image_alt": bool(main_image and main_image.get("alt")),
        "inline_images": len(img_tags),
        "figures": figure_count,
        "blockquotes": blockquote_count,
        "tables": table_count,
        "responsive_tables": responsive_tables,
        "errors": errors,
        "warnings": warnings,
        # Additional fields
        "empty_fields": empty_fields,
        "meta_description": (
            meta_desc[:50] + "..." if len(meta_desc) > 50 else meta_desc
        ),
        "meta_desc_length": len(meta_desc),
        "summary_html": bool(summary_html),
        "author": author,
        "tags": tags,
        "handle": handle,
        "published_at": published_at,
        # SEO metrics
        "title_length": len(title),
        "h2_count": h2_count,
        "h3_count": h3_count,
        "lists_count": total_lists,
        "internal_links": internal_links,
        # META-PROMPT metrics
        "sources_links": sources_links_count,
        "valid_quotes": valid_quotes,
        "stats_found": stats_found,
        "headings_with_id": len(headings_with_id),
        "headings_without_id": headings_without_id,
    }


def print_review(result):
    """Print formatted review result"""
    status = "✅ PASS" if result["passed"] else "❌ FAIL"

    print(f"\n{'='*70}")
    print(f"ARTICLE: {result['title'][:50]}")
    print(f"ID: {result['article_id']}")
    print(f"STATUS: {status}")
    print(f"{'='*70}")

    print(f"\nCONTENT METRICS:")
    print(f"  Words: {result['word_count']} (need 1800-2200)")
    print(f"  Main Image: {'✅' if result['main_image'] else '❌'}")
    print(f"  Main Image Alt: {'✅' if result['main_image_alt'] else '❌'}")
    print(f"  Inline Images: {result['inline_images']} (need 3+)")
    print(f"  Figures: {result['figures']} (need 3+)")
    print(f"  Blockquotes: {result['blockquotes']} (need 2+)")
    tables_status = "✅" if result["tables"] >= 1 else "❌"
    responsive_status = (
        "✅" if result.get("responsive_tables", 0) >= result["tables"] else "⚠️"
    )
    print(f"  Tables: {tables_status} {result['tables']} (need 1+)")
    print(
        f"  Mobile Responsive Tables: {responsive_status} {result.get('responsive_tables', 0)}/{result['tables']}"
    )

    print(f"\nSEO METRICS:")
    title_len_status = "✅" if 30 <= result["title_length"] <= 60 else "⚠️"
    print(
        f"  Title Length: {title_len_status} {result['title_length']} chars (need 30-60)"
    )
    print(f"  H2 Headings: {result.get('h2_count', 0)}")
    print(f"  H3 Headings: {result.get('h3_count', 0)}")
    print(f"  Lists (ul/ol): {result.get('lists_count', 0)} (need 2+)")
    internal_status = "✅" if result.get("internal_links", 0) >= 2 else "⚠️"
    print(
        f"  Internal Links: {internal_status} {result.get('internal_links', 0)} (need 2+)"
    )

    print(f"\nMETA-PROMPT COMPLIANCE:")
    sources_status = "✅" if result.get("sources_links", 0) >= 5 else "❌"
    print(
        f"  Sources/Citations: {sources_status} {result.get('sources_links', 0)} (need 5+)"
    )
    quotes_status = "✅" if result.get("valid_quotes", 0) >= 2 else "⚠️"
    print(f"  Expert Quotes: {quotes_status} {result.get('valid_quotes', 0)} (need 2+)")
    stats_status = "✅" if result.get("stats_found", 0) >= 3 else "⚠️"
    print(
        f"  Quantified Stats: {stats_status} {result.get('stats_found', 0)} (need 3+)"
    )
    ids_status = "✅" if result.get("headings_without_id", 0) == 0 else "⚠️"
    print(
        f"  Heading IDs: {ids_status} {result.get('headings_with_id', 0)} with id, {result.get('headings_without_id', 0)} missing"
    )

    print(f"\nFIELD STATUS:")
    print(f"  Handle: {'✅ ' + result['handle'] if result['handle'] else '❌ Empty'}")
    print(f"  Author: {'✅ ' + result['author'] if result['author'] else '⚠️ Empty'}")
    print(
        f"  Tags: {'✅ ' + result['tags'][:30] + '...' if result['tags'] and len(result['tags']) > 30 else ('✅ ' + result['tags'] if result['tags'] else '⚠️ Empty')}"
    )
    meta_status = (
        "✅"
        if result["meta_desc_length"] >= 50 and result["meta_desc_length"] <= 160
        else ("⚠️" if result["meta_desc_length"] > 0 else "❌")
    )
    print(
        f"  Meta Description: {meta_status} ({result['meta_desc_length']} chars, need 50-160)"
    )
    print(f"  Summary HTML: {'✅' if result['summary_html'] else '⚠️ Empty'}")
    print(
        f"  Published: {'✅ ' + result['published_at'][:10] if result['published_at'] else '⚠️ Draft'}"
    )

    if result.get("empty_fields"):
        print(
            f"\nEMPTY FIELDS ({len(result['empty_fields'])}): {', '.join(result['empty_fields'])}"
        )

    if result["errors"]:
        print(f"\nERRORS ({len(result['errors'])}):")
        for err in result["errors"]:
            print(f"  {err}")

    if result["warnings"]:
        print(f"\nWARNINGS ({len(result['warnings'])}):")
        for warn in result["warnings"]:
            print(f"  {warn}")

    return result["passed"]


def review_all(article_ids):
    """Review all articles and return summary"""
    print("=" * 70)
    print("PRE-PUBLISH REVIEW CHECKLIST")
    print("META-PROMPT Compliance Check")
    print("=" * 70)

    all_passed = True
    results = []

    for aid in article_ids:
        result = review_article(aid)
        results.append(result)
        passed = print_review(result)
        if not passed:
            all_passed = False

    # Final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"\nPassed: {passed_count}/{total}")

    if all_passed:
        print("\n✅ ALL ARTICLES READY FOR PUBLISH")
        return True
    else:
        print("\n❌ SOME ARTICLES NEED FIXES BEFORE PUBLISH")
        print("\nFailed articles:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['article_id']}: {r['title'][:40]}")
        return False


if __name__ == "__main__":
    # Default: review the 10 new articles
    ARTICLE_IDS = [
        690513117502,
        690513150270,
        690513183038,
        690513215806,
        690513248574,
        690513281342,
        690513314110,
        690513346878,
        690513379646,
        690513412414,
    ]

    # Allow passing specific article IDs
    if len(sys.argv) > 1:
        ARTICLE_IDS = [int(aid) for aid in sys.argv[1:]]

    success = review_all(ARTICLE_IDS)
    sys.exit(0 if success else 1)
