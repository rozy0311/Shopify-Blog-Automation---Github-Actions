#!/usr/bin/env python3
"""
run_one_topic.py - Single topic pipeline runner.

Orchestrates the full pipeline for one topic:
1. Research (via external tools/APIs)
2. Generate article payload + evidence ledger
3. Generate images (4 photorealistic images)
4. Run validator
5. Run reviewer gate
6. Publish to Shopify (if both gates pass)

This script is meant to be called by batch_publish.py or run standalone.

Usage:
    python scripts/run_one_topic.py --topic "How to Make Homemade Vinegar"
    python scripts/run_one_topic.py --topic "..." --dry-run

Note: This is a scaffold. The actual content generation would typically
be done by an LLM agent (VSCode Copilot, OpenAI, etc.) that:
- Uses webSearch + fetch_webpage for research
- Generates HTML following the meta-prompt
- Creates image prompts
"""

import argparse
import json
import subprocess
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent
CONTENT_DIR = ROOT_DIR / "content"
CONFIG_PATH = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"


def load_config() -> dict:
    """Load configuration."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def sha256(s: str) -> str:
    """Compute SHA256 hash."""
    return hashlib.sha256(s.strip().encode("utf-8")).hexdigest()


def init_content_dir():
    """Ensure content directory exists."""
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)


def create_evidence_ledger_template(topic: str) -> dict:
    """Create empty evidence ledger template."""
    return {
        "topic": topic,
        "created_at": datetime.now().isoformat(),
        "sources": [],
        "stats": [],
        "quotes": [],
        "facts": [],
    }


def create_article_payload_template(topic: str, config: dict) -> dict:
    """Create article payload template."""
    defaults = config.get("defaults", {})

    return {
        "topic": topic,
        "primary_keyword": "",
        "title": "",
        "seo_title": "",
        "meta_desc": "",
        "body_html": "",
        "schema_jsonld": "",
        "blog_handle": defaults.get("blog_handle", "sustainable-living"),
        "author_name": defaults.get("author_name", "The Rike"),
        "tags": [],
        "handle": "",
        "publish": defaults.get("publish_mode", "draft"),
        "strict_no_years": config.get("content", {}).get("strict_no_years", True),
        "featured_image_url": "",
        "featured_image_alt": "",
        "inline_images": [],
        "metafields": [],
    }


def create_image_plan_template(topic: str) -> dict:
    """Create image plan template."""
    return {
        "topic": topic,
        "style": {
            "camera": "50mm lens, f/2.8, ISO 200, 1/125s",
            "lighting": "natural window light, soft shadows",
            "quality": "photorealistic, ultra-detailed, high resolution",
        },
        "negative_prompt": "people, hands, faces, logos, text, labels, watermarks, brand marks, cartoon, illustration, painting, drawing, CGI, 3D render, blurry, low resolution",
        "main_image": {
            "filename": "main.jpg",
            "prompt": "",
            "alt": "",
            "section": "hero",
        },
        "inline_images": [
            {
                "filename": "inline_1.jpg",
                "prompt": "",
                "alt": "",
                "insert_after_section_id": "prep",
            },
            {
                "filename": "inline_2.jpg",
                "prompt": "",
                "alt": "",
                "insert_after_section_id": "process",
            },
            {
                "filename": "inline_3.jpg",
                "prompt": "",
                "alt": "",
                "insert_after_section_id": "troubleshooting",
            },
        ],
    }


def create_qa_report_template() -> dict:
    """Create QA report template."""
    return {
        "validator_pass": False,
        "reviewer_pass": False,
        "validator_errors": [],
        "reviewer_errors": [],
        "computed": {
            "word_count": 0,
            "sources_links": 0,
            "quotes_count": 0,
            "stats_markers": 0,
            "image_count": 0,
        },
        "created_at": datetime.now().isoformat(),
    }


def run_validator() -> bool:
    """Run the validator script."""
    payload_path = CONTENT_DIR / "article_payload.json"

    if not payload_path.exists():
        print("❌ article_payload.json not found")
        return False

    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "validate_article.py"), str(payload_path)],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def run_reviewer() -> bool:
    """
    Run reviewer gate.

    The reviewer checks:
    1. Claims in article match evidence_ledger
    2. Stats have [EVID:STAT_N] markers matching ledger
    3. Quotes have [EVID:QUOTE_N] markers matching ledger
    4. Topic/title consistency
    5. No fabricated sources

    For a full implementation, this would use an LLM to verify claims.
    This scaffold performs basic structural checks.
    """
    print("\n📋 Running Reviewer Gate...")

    payload_path = CONTENT_DIR / "article_payload.json"
    ledger_path = CONTENT_DIR / "evidence_ledger.json"
    qa_path = CONTENT_DIR / "qa_report.json"

    errors = []

    # Load files
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"Cannot load files: {e}")
        update_qa_report(qa_path, reviewer_pass=False, reviewer_errors=errors)
        return False

    body_html = payload.get("body_html", "")

    # Check 1: Sources in article should exist in ledger
    ledger_urls = {s.get("url") for s in ledger.get("sources", []) if s.get("url")}

    # Check 2: Stats markers should reference valid ledger entries
    import re

    stat_markers = re.findall(r"\[EVID:STAT_(\d+)\]", body_html)
    ledger_stats_count = len(ledger.get("stats", []))

    for marker_num in stat_markers:
        if int(marker_num) > ledger_stats_count:
            errors.append(
                f"Stat marker [EVID:STAT_{marker_num}] references non-existent ledger entry"
            )

    # Check 3: Quote markers should reference valid ledger entries
    quote_markers = re.findall(r"\[EVID:QUOTE_(\d+)\]", body_html)
    ledger_quotes_count = len(ledger.get("quotes", []))

    for marker_num in quote_markers:
        if int(marker_num) > ledger_quotes_count:
            errors.append(
                f"Quote marker [EVID:QUOTE_{marker_num}] references non-existent ledger entry"
            )

    # Check 4: Minimum evidence thresholds
    config = load_config()
    content_config = config.get("content", {})

    if len(ledger.get("sources", [])) < content_config.get("min_citations", 5):
        errors.append(
            f"Insufficient sources in ledger: {len(ledger.get('sources', []))} < 5"
        )

    if len(ledger.get("quotes", [])) < content_config.get("min_quotes", 2):
        errors.append(
            f"Insufficient quotes in ledger: {len(ledger.get('quotes', []))} < 2"
        )

    if len(ledger.get("stats", [])) < content_config.get("min_stats", 3):
        errors.append(
            f"Insufficient stats in ledger: {len(ledger.get('stats', []))} < 3"
        )

    # Check 5: Topic/title consistency
    topic = payload.get("topic", "").lower()
    title = payload.get("title", "").lower()
    primary_keyword = payload.get("primary_keyword", "").lower()

    if primary_keyword and primary_keyword not in title:
        errors.append(f"Primary keyword '{primary_keyword}' not found in title")

    # Update QA report
    reviewer_pass = len(errors) == 0
    update_qa_report(qa_path, reviewer_pass=reviewer_pass, reviewer_errors=errors)

    if errors:
        print("❌ REVIEWER FAIL")
        for e in errors:
            print(f"  - {e}")
    else:
        print("✅ REVIEWER PASS")

    return reviewer_pass


def update_qa_report(qa_path: Path, **updates):
    """Update QA report with new values."""
    try:
        if qa_path.exists():
            qa = json.loads(qa_path.read_text(encoding="utf-8"))
        else:
            qa = create_qa_report_template()
    except Exception:
        qa = create_qa_report_template()

    qa.update(updates)
    qa["updated_at"] = datetime.now().isoformat()

    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")


def run_publisher(dry_run: bool = False) -> bool:
    """Run the publisher script."""
    if dry_run:
        print("\n🔄 DRY RUN: Would publish article (skipping)")
        return True

    payload_path = CONTENT_DIR / "article_payload.json"

    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "publish_article.py"), str(payload_path)],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr)

    return result.returncode == 0


def main():
    """Main pipeline runner."""
    parser = argparse.ArgumentParser(description="Run full blog pipeline for one topic")
    parser.add_argument("--topic", required=True, help="Topic to process")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual publishing")
    args = parser.parse_args()

    topic = args.topic
    dry_run = args.dry_run

    print("\n" + "=" * 60)
    print("SINGLE TOPIC PIPELINE")
    print("=" * 60)
    print(f"Topic: {topic}")
    print(f"Dry run: {dry_run}")

    # Initialize
    init_content_dir()
    config = load_config()

    # Create template files
    # In a real implementation, an LLM agent would fill these
    evidence_ledger = create_evidence_ledger_template(topic)
    article_payload = create_article_payload_template(topic, config)
    image_plan = create_image_plan_template(topic)
    qa_report = create_qa_report_template()

    # Save templates (these would be populated by LLM agent)
    (CONTENT_DIR / "evidence_ledger.json").write_text(
        json.dumps(evidence_ledger, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (CONTENT_DIR / "article_payload.json").write_text(
        json.dumps(article_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (CONTENT_DIR / "image_plan.json").write_text(
        json.dumps(image_plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (CONTENT_DIR / "qa_report.json").write_text(
        json.dumps(qa_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\n📄 Created template files in content/")
    print("   - evidence_ledger.json")
    print("   - article_payload.json")
    print("   - image_plan.json")
    print("   - qa_report.json")

    print("\n" + "=" * 60)
    print("⚠️  SCAFFOLD MODE")
    print("=" * 60)
    print(
        """
This script has created template files for the pipeline.
In production, an LLM agent (VSCode Copilot) would:

1. RESEARCH PASS:
   - Use webSearch to find sources
   - Use fetch_webpage to read each source
   - Extract facts, stats, quotes into evidence_ledger.json

2. WRITE PASS:
   - Generate article HTML following the meta-prompt
   - Populate article_payload.json with full content
   - Mark claims with [EVID:STAT_N] and [EVID:QUOTE_N]

3. IMAGE PASS:
   - Generate 4 photorealistic image prompts
   - Upload to Shopify Files
   - Update article_payload with image URLs

4. VALIDATE + REVIEW:
   - Run validate_article.py
   - Run reviewer gate (this script)

5. PUBLISH:
   - Run publish_article.py

To test the pipeline with sample data, populate:
   content/article_payload.json
   content/evidence_ledger.json

Then run:
   python scripts/validate_article.py content/article_payload.json

And if validation passes, manually set reviewer_pass=true in qa_report.json,
then run:
   python scripts/publish_article.py content/article_payload.json
"""
    )

    # In a full implementation, we would:
    # 1. Call LLM to research and generate content
    # 2. Run validator
    # 3. Run reviewer
    # 4. Publish if both pass

    # For now, just check if content exists and run gates
    payload_path = CONTENT_DIR / "article_payload.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))

    # Check if this is just a template (no actual content)
    if not payload.get("body_html"):
        print("\n⏸️  Template mode: No content generated yet")
        print("   Populate article_payload.json with content to continue")
        sys.exit(0)

    # Run validation
    print("\n📋 Running Validator...")
    validator_pass = run_validator()

    if not validator_pass:
        print("\n❌ Pipeline stopped: Validator failed")
        sys.exit(2)

    # Run reviewer
    reviewer_pass = run_reviewer()

    if not reviewer_pass:
        print("\n❌ Pipeline stopped: Reviewer failed")
        sys.exit(2)

    # Publish
    print("\n📤 Publishing to Shopify...")
    publish_success = run_publisher(dry_run)

    if not publish_success:
        print("\n❌ Pipeline stopped: Publish failed")
        sys.exit(2)

    print("\n✅ Pipeline completed successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
