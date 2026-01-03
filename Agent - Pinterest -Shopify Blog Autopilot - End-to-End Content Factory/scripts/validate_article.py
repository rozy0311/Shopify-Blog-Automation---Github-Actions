#!/usr/bin/env python3
"""
validate_article.py - Validator script for Shopify blog articles.

Validates article payload against hard rules:
- Word count within budget
- SEO title/meta desc length
- No year tokens if strict_no_years
- All H2/H3 have unique kebab-case ids
- All links absolute HTTPS with rel="nofollow noopener"
- Minimum citations, quotes, stats
- Schema NOT inside HTML body
- Images have alt text

Usage:
    python scripts/validate_article.py content/article_payload.json
"""

import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

# Regex patterns
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STAT_MARKER_RE = re.compile(r"\[EVID:STAT_\d+\]")
QUOTE_MARKER_RE = re.compile(r"\[EVID:QUOTE_\d+\]")

# Load config
CONFIG_PATH = Path(__file__).parent.parent / "SHOPIFY_PUBLISH_CONFIG.json"


def load_config():
    """Load configuration from SHOPIFY_PUBLISH_CONFIG.json"""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "content": {
            "word_budget_min": 1800,
            "word_budget_max": 2200,
            "min_citations": 5,
            "min_quotes": 2,
            "min_stats": 3,
            "strict_no_years": True,
        },
        "seo": {"seo_title_max_chars": 60, "meta_desc_max_chars": 155},
    }


def word_count_from_html(html: str) -> int:
    """Extract word count from HTML content."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    return len([w for w in re.split(r"\s+", text) if w])


def fail(errors: list, msg: str):
    """Append error message to errors list."""
    errors.append(msg)


def validate_required_fields(payload: dict, errors: list):
    """Check all required fields are present and non-empty."""
    required = [
        "title",
        "seo_title",
        "meta_desc",
        "body_html",
        "schema_jsonld",
        "blog_handle",
        "author_name",
    ]
    for key in required:
        if not payload.get(key):
            fail(errors, f"Missing required field: {key}")


def validate_seo_lengths(payload: dict, config: dict, errors: list):
    """Validate SEO title and meta description lengths."""
    seo_config = config.get("seo", {})
    seo_title = payload.get("seo_title", "")
    meta_desc = payload.get("meta_desc", "")

    max_seo_title = seo_config.get("seo_title_max_chars", 60)
    max_meta_desc = seo_config.get("meta_desc_max_chars", 155)

    if len(seo_title) > max_seo_title:
        fail(errors, f"SEO_TITLE > {max_seo_title} chars (got {len(seo_title)})")
    if len(meta_desc) > max_meta_desc:
        fail(errors, f"META_DESC > {max_meta_desc} chars (got {len(meta_desc)})")


def validate_no_years(payload: dict, errors: list):
    """Check no year tokens if strict_no_years is enabled (excluding URLs)."""
    # Create a copy of payload and strip URLs before checking
    import copy

    payload_copy = copy.deepcopy(payload)
    blob = json.dumps(payload_copy, ensure_ascii=False)
    # Remove URLs from the blob before year checking
    url_pattern = re.compile(r'https?://[^\s"\'<>]+')
    blob_no_urls = url_pattern.sub("", blob)
    if YEAR_RE.search(blob_no_urls):
        fail(errors, "Found year token (YYYY) while strict_no_years=true")


def validate_schema_not_in_html(body_html: str, errors: list):
    """Ensure JSON-LD schema is not embedded in HTML body."""
    if re.search(r"application/ld\+json", body_html, re.IGNORECASE):
        fail(errors, "Schema JSON-LD appears inside body_html (not allowed)")


def validate_headings(soup: BeautifulSoup, errors: list) -> list:
    """Validate all H2/H3 have unique kebab-case ids."""
    ids = []
    for tag in soup.find_all(["h2", "h3"]):
        heading_id = tag.get("id")
        heading_text = tag.get_text(strip=True)[:60]

        if not heading_id:
            fail(errors, f"Missing id on heading: {heading_text}")
        else:
            if not KEBAB_RE.match(heading_id):
                fail(errors, f"Heading id not kebab-case: {heading_id}")
            ids.append(heading_id)

    if len(ids) != len(set(ids)):
        fail(errors, "Duplicate heading ids found")

    return ids


def validate_links(soup: BeautifulSoup, errors: list):
    """Validate all outbound links are absolute HTTPS with proper rel attributes."""
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()

        # Skip internal anchors
        if href.startswith("#"):
            continue

        if not href.startswith("https://"):
            fail(errors, f"Non-HTTPS or non-absolute link: {href}")

        rel = a.get("rel") or []
        rel_set = (
            {r.lower() for r in rel}
            if isinstance(rel, list)
            else set(str(rel).lower().split())
        )

        if "nofollow" not in rel_set or "noopener" not in rel_set:
            fail(errors, f"Link missing rel nofollow+noopener: {href}")


def validate_sources_section(
    soup: BeautifulSoup, min_citations: int, errors: list
) -> int:
    """Validate sources section has minimum required citations."""
    sources_h2 = soup.find(id="sources")
    if not sources_h2:
        fail(errors, 'Missing <h2 id="sources"> section')
        return 0

    sources_links = 0
    for sib in sources_h2.find_all_next():
        if sib.name == "h2" and sib.get("id") != "sources":
            break
        if sib.name == "a" and (sib.get("href") or "").startswith("https://"):
            sources_links += 1

    if sources_links < min_citations:
        fail(errors, f"Need >={min_citations} sources links, found {sources_links}")

    return sources_links


def validate_quotes(soup: BeautifulSoup, min_quotes: int, errors: list) -> int:
    """Validate minimum number of blockquote elements for expert quotes."""
    quotes_count = len(soup.find_all("blockquote"))
    if quotes_count < min_quotes:
        fail(
            errors,
            f"Need >={min_quotes} blockquotes for expert quotes, found {quotes_count}",
        )
    return quotes_count


def validate_stats_markers(body_html: str, min_stats: int, errors: list) -> int:
    """Validate minimum number of stat evidence markers."""
    stats_count = len(STAT_MARKER_RE.findall(body_html))
    if stats_count < min_stats:
        fail(errors, f"Need >={min_stats} [EVID:STAT_N] markers, found {stats_count}")
    return stats_count


def validate_images(soup: BeautifulSoup, errors: list) -> int:
    """Validate all images have alt text and HTTPS src."""
    images = soup.find_all("img")
    image_count = 0

    for img in images:
        src = img.get("src", "")
        alt = img.get("alt", "")

        if not src.startswith("https://"):
            fail(errors, f"Image src not HTTPS: {src[:50]}")
        if not alt or alt.strip() == "":
            fail(errors, f"Image missing alt text: {src[:50]}")

        image_count += 1

    return image_count


def validate_word_count(body_html: str, config: dict, errors: list) -> int:
    """Validate word count is within budget."""
    content_config = config.get("content", {})
    min_words = content_config.get("word_budget_min", 1800)
    max_words = content_config.get("word_budget_max", 2200)

    wc = word_count_from_html(body_html)
    if wc < min_words or wc > max_words:
        fail(errors, f"Word count out of band ({min_words}-{max_words}): {wc}")

    return wc


def validate_evidence_ledger(payload: dict, errors: list):
    """Cross-check claims against evidence ledger if available."""
    evidence_path = Path(__file__).parent.parent / "content" / "evidence_ledger.json"
    if not evidence_path.exists():
        return

    try:
        ledger = json.loads(evidence_path.read_text(encoding="utf-8"))
        body_html = payload.get("body_html", "")

        # Check stat markers reference valid evidence
        stat_markers = STAT_MARKER_RE.findall(body_html)
        quote_markers = QUOTE_MARKER_RE.findall(body_html)

        ledger_stats = {
            f"[EVID:STAT_{i+1}]" for i in range(len(ledger.get("stats", [])))
        }
        ledger_quotes = {
            f"[EVID:QUOTE_{i+1}]" for i in range(len(ledger.get("quotes", [])))
        }

        for marker in stat_markers:
            if marker not in ledger_stats:
                fail(errors, f"Stat marker {marker} not found in evidence_ledger")

        for marker in quote_markers:
            if marker not in ledger_quotes:
                fail(errors, f"Quote marker {marker} not found in evidence_ledger")

    except Exception as e:
        fail(errors, f"Error reading evidence_ledger: {str(e)}")


def main(payload_path: str):
    """Main validation function."""
    errors = []
    config = load_config()
    content_config = config.get("content", {})

    # Load payload
    try:
        with open(payload_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        print(f"VALIDATION FAIL: Cannot load payload: {e}")
        sys.exit(2)

    # Run validations
    validate_required_fields(payload, errors)
    validate_seo_lengths(payload, config, errors)

    body_html = payload.get("body_html", "")

    # Strict no years check
    if content_config.get("strict_no_years", True):
        validate_no_years(payload, errors)

    validate_schema_not_in_html(body_html, errors)

    soup = BeautifulSoup(body_html, "html.parser")

    validate_headings(soup, errors)
    validate_links(soup, errors)

    sources_links = validate_sources_section(
        soup, content_config.get("min_citations", 5), errors
    )

    quotes_count = validate_quotes(soup, content_config.get("min_quotes", 2), errors)

    stats_count = validate_stats_markers(
        body_html, content_config.get("min_stats", 3), errors
    )

    image_count = validate_images(soup, errors)
    word_count = validate_word_count(body_html, config, errors)

    validate_evidence_ledger(payload, errors)

    # Build report
    report = {
        "validator_pass": len(errors) == 0,
        "validator_errors": errors,
        "computed": {
            "word_count": word_count,
            "sources_links": sources_links,
            "quotes_count": quotes_count,
            "stats_markers": stats_count,
            "image_count": image_count,
        },
    }

    # Update qa_report.json
    qa_report_path = Path(__file__).parent.parent / "content" / "qa_report.json"
    try:
        if qa_report_path.exists():
            existing = json.loads(qa_report_path.read_text(encoding="utf-8"))
        else:
            existing = {}
    except Exception:
        existing = {}

    existing.update(report)
    qa_report_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Output result
    if errors:
        print("VALIDATION FAIL")
        for e in errors:
            print(f"  - {e}")
        sys.exit(2)

    print("VALIDATION PASS")
    print(f"  Word count: {word_count}")
    print(f"  Sources: {sources_links}")
    print(f"  Quotes: {quotes_count}")
    print(f"  Stats: {stats_count}")
    print(f"  Images: {image_count}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_article.py content/article_payload.json")
        sys.exit(1)
    main(sys.argv[1])
