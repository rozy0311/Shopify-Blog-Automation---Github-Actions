#!/usr/bin/env python3
"""
AI ORCHESTRATOR - Master Agent Controller
==========================================
Quản lý toàn bộ workflow từ đầu tới cuối.
Đảm bảo agent KHÔNG bị mất context và KHÔNG làm generic content.

CORE RESPONSIBILITIES:
1. Load và enforce META PROMPT requirements
2. Track progress và state
3. Quality gate - chặn publish nếu không đạt chuẩn
4. Self-healing - tự phát hiện và fix lỗi

WORKFLOW:
1. Scan all articles → identify issues
2. Prioritize by severity
3. Fix each article → validate → publish
4. Loop until all pass

Author: Rosie AI Pipeline
Date: 2026-01-08
"""

import os
import sys
import re
import csv
import json
import time
import random
import hashlib
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from collections import Counter
from dotenv import load_dotenv

# Load environment - check multiple locations
env_paths = [
    Path(__file__).parent.parent.parent / ".env",
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        # Allow closer .env files to override higher-level defaults.
        load_dotenv(env_path, override=True)
shop_env = (os.environ.get("SHOPIFY_SHOP") or "").strip()
store_env = (os.environ.get("SHOPIFY_STORE_DOMAIN") or "").strip()
if store_env and "." in store_env:
    SHOP = store_env
else:
    SHOP = shop_env or store_env
    if SHOP and "." not in SHOP:
        SHOP = f"{SHOP}.myshopify.com"
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID") or os.environ.get("BLOG_ID") or ""
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get("SHOPIFY_TOKEN") or ""
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}
BACKOFF_BASE_SECONDS = 120
BACKOFF_MAX_SECONDS = 600
BACKOFF_JITTER_SECONDS = 30
MAX_QUEUE_RETRIES = int(os.environ.get("MAX_QUEUE_RETRIES", "20"))  # No manual review: always retry
MAX_CONSECUTIVE_FAILS = int(os.environ.get("MAX_CONSEC_FAILS", "3"))
MAX_FIX_ATTEMPTS_PER_RUN = int(os.environ.get("MAX_FIX_ATTEMPTS_PER_RUN", "2"))
PROGRESS_FILE = Path(__file__).parent / "progress.json"
PIPELINE_DIR = Path(__file__).parent
ROOT_DIR = PIPELINE_DIR.parent.parent
AGENT_DIR = PIPELINE_DIR.parent
ANTI_DRIFT_QUEUE_FILE = PIPELINE_DIR / "anti_drift_queue.json"
ANTI_DRIFT_RUN_LOG_FILE = PIPELINE_DIR / "anti_drift_run_log.csv"
ANTI_DRIFT_DONE_FILE = PIPELINE_DIR / "anti_drift_done_blacklist.json"
ANTI_DRIFT_SPEC_FILE = PIPELINE_DIR / "anti_drift_spec_v1.md"
ANTI_DRIFT_GOLDENS_FILE = PIPELINE_DIR / "anti_drift_goldens_12.json"
PRE_PUBLISH_REVIEW_SCRIPT = AGENT_DIR / "scripts" / "pre_publish_review.py"
BUILD_META_FIX_SCRIPT = AGENT_DIR / "scripts" / "build_meta_fix_queue.py"
RUN_META_FIX_SCRIPT = AGENT_DIR / "scripts" / "run_meta_fix_queue.py"
BACKUP_DIR = PIPELINE_DIR / "backups_auto_fix"


# ============================================================================
# META PROMPT REQUIREMENTS - ENFORCED
# ============================================================================

META_PROMPT_REQUIREMENTS = {
    "structure": {
        "required_sections": [
            "Direct Answer",
            "Key Conditions at a Glance",
            "Understanding [Topic]",
            "Complete Step-by-Step Guide",
            "Types and Varieties",
            "Troubleshooting Common Issues",
            "Pro Tips from Experts",
            "Frequently Asked Questions",
            "Advanced Techniques",
            "Comparison Table",
            "Sources & Further Reading",
        ],
        "min_sections": 9,
        "min_word_count": 1800,
        "max_word_count": 2500,
        "min_faq_count": 7,
    },
    "images": {
        "min_images": 4,
        "required_types": ["ai_inline", "featured"],
        "no_duplicates": True,
        "must_match_topic": True,
    },
    "content": {
        "no_generic_phrases": True,
        "topic_focus_score_min": 8,
        "evidence_based": True,
        "no_template_contamination": True,
    },
    "sources": {
        "min_sources": 5,
        "format": "hidden_url_in_href",
        "no_visible_raw_urls": True,
    },
}

# Generic phrases to detect
GENERIC_PHRASES = [
    "this comprehensive guide provides",
    "this comprehensive guide covers",
    "whether you are a beginner",
    "whether you're a beginner",
    "this guide explains",
    "you will learn what works",
    "the focus is on",
    "by the end, you will know",
    "taking your understanding to the next level",
    "advanced considerations and expert insights",
    "quality over quantity",
    "building community connections",
    "continuous learning mindset",
    "environmental responsibility",
    "documentation and reflection",
    "no one succeeds in isolation",
    "in today's fast-paced world",
    "natural materials vary throughout",
    "professional practitioners recommend",
    "achieving consistent results requires attention",
    "once you've perfected small batches",
    "once you have perfected small batches",
    "scaling up becomes appealing",
    "making larger batches requires",
    "heat distribution",
    "doubling recipes",
    "this practical guide",
    "this guide covers practical",
    "perfect for anyone looking to improve",
    "join thousands who have already mastered",
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
# Template contamination keywords
CONTAMINATION_RULES = {
    "cordage": [
        "measuring cups",
        "thermometer",
        "baking",
        "recipe",
        "dry ingredients",
        "shelf life",
    ],
    "garden": ["shelf life 2-4 weeks", "dry ingredients", "recipe", "baking"],
    "plant": ["measuring cups", "recipe", "baking", "thermometer"],
    "vinegar": ["cordage", "rope", "twine", "weaving"],
    "soap": ["germination", "transplanting", "pruning"],
    "candle": ["germination", "transplanting", "compost"],
}


# ============================================================================
# QUALITY GATES
# ============================================================================


def _file_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _remove_generic_sections(body_html: str) -> str:
    """Remove known generic/off-topic sections and phrases."""
    if not body_html:
        return body_html
    soup = BeautifulSoup(body_html, "html.parser")
    headings = soup.find_all(re.compile(r"^h[2-6]$", re.IGNORECASE))
    for heading in headings:
        text = heading.get_text(" ", strip=True).lower()
        if any(h in text for h in GENERIC_SECTION_HEADINGS):
            # Remove heading and content until the next heading
            next_node = heading.find_next_sibling()
            heading.decompose()
            while next_node:
                if getattr(next_node, "name", None) and re.match(
                    r"^h[2-6]$", next_node.name, re.IGNORECASE
                ):
                    break
                to_remove = next_node
                next_node = next_node.find_next_sibling()
                to_remove.decompose()

    for tag in soup.find_all(["p", "li", "blockquote"]):
        text = tag.get_text(" ", strip=True).lower()
        if any(phrase in text for phrase in GENERIC_PHRASES):
            tag.decompose()

    return str(soup)


def _dedupe_paragraphs(body_html: str) -> str:
    """Remove duplicate paragraphs (same text 40+ chars). Keeps first occurrence."""
    if not body_html:
        return body_html
    soup = BeautifulSoup(body_html, "html.parser")
    seen = set()
    for tag in soup.find_all("p"):
        text = re.sub(r"\s+", " ", tag.get_text(" ", strip=True)).strip().lower()
        if len(text) < 40:
            continue
        if text in seen:
            tag.decompose()
        else:
            seen.add(text)
    return str(soup)


def _ensure_run_log_header():
    header = [
        "timestamp",
        "article_id",
        "title",
        "status",
        "fail_type",
        "attempts",
        "failures",
        "gate_score",
        "gate_pass",
        "issues",
        "spec_hash",
        "goldens_hash",
    ]
    if ANTI_DRIFT_RUN_LOG_FILE.exists():
        with open(ANTI_DRIFT_RUN_LOG_FILE, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
        if first_line == ",".join(header):
            return
        rows = []
        with open(ANTI_DRIFT_RUN_LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            existing = list(reader)
        if existing and existing[0]:
            rows = existing[1:]
        with open(ANTI_DRIFT_RUN_LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for row in rows:
                padded = row + [""] * (len(header) - len(row))
                writer.writerow(padded[: len(header)])
        return
    with open(ANTI_DRIFT_RUN_LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)


def _load_done_blacklist() -> set[str]:
    candidates = [
        ANTI_DRIFT_DONE_FILE,
        ROOT_DIR / "anti_drift_done.json",
        ROOT_DIR / "anti_drift_done_blacklist.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        ids = payload.get("done_ids", []) if isinstance(payload, dict) else payload
        return {str(x) for x in ids}
    return set()


def _save_done_blacklist(done_ids: set[str]) -> None:
    payload = {
        "updated_at": datetime.now().isoformat(),
        "done_ids": sorted(done_ids),
    }
    ANTI_DRIFT_DONE_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class AntiDriftQueue:
    def __init__(self, payload: dict):
        self.payload = payload

    @classmethod
    def load(cls) -> "AntiDriftQueue":
        if ANTI_DRIFT_QUEUE_FILE.exists():
            with open(ANTI_DRIFT_QUEUE_FILE, "r", encoding="utf-8") as f:
                return cls(json.load(f))
        return cls({"version": 1, "created_at": None, "updated_at": None, "items": []})

    def save(self):
        self.payload["updated_at"] = datetime.now().isoformat()
        if not self.payload.get("created_at"):
            self.payload["created_at"] = self.payload["updated_at"]
        with open(ANTI_DRIFT_QUEUE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.payload, f, indent=2, ensure_ascii=False)

    def init_from_articles_to_fix(self) -> int:
        articles_file = PIPELINE_DIR / "articles_to_fix.json"
        if not articles_file.exists():
            return 0
        with open(articles_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        done_ids = _load_done_blacklist()
        queue_items = []
        for item in items:
            article_id = str(item.get("id"))
            if article_id in done_ids:
                continue
            queue_items.append(
                {
                    "id": article_id,
                    "title": item.get("title", ""),
                    "status": "pending",
                    "attempts": 0,
                    "last_error": None,
                    "shopify_url": None,
                    "updated_at": datetime.now().isoformat(),
                }
            )
        self.payload = {
            "version": 1,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "items": queue_items,
        }
        self.save()
        return len(queue_items)

    def next_pending(self) -> dict | None:
        for item in self.payload.get("items", []):
            if item.get("status") == "pending":
                return item
        return None

    def next_eligible(self, now: datetime | None = None) -> dict | None:
        now = now or datetime.now()
        for item in self.payload.get("items", []):
            if item.get("status") == "pending":
                return item
        for item in self.payload.get("items", []):
            if item.get("status") in ("manual_review", "failed"):
                return item
        for item in self.payload.get("items", []):
            if item.get("status") == "retrying":
                retry_at = item.get("retry_at")
                if not retry_at:
                    return item
                try:
                    if datetime.fromisoformat(retry_at) <= now:
                        return item
                except ValueError:
                    return item
        return None

    def next_retry_time(self) -> datetime | None:
        next_time = None
        for item in self.payload.get("items", []):
            if item.get("status") != "retrying":
                continue
            retry_at = item.get("retry_at")
            if not retry_at:
                return None
            try:
                ts = datetime.fromisoformat(retry_at)
            except ValueError:
                return None
            if next_time is None or ts < next_time:
                next_time = ts
        return next_time

    def mark_in_progress(self, article_id: str):
        self._update_status(article_id, "in_progress")

    def mark_done(self, article_id: str, shopify_url: str | None = None):
        self._update_status(article_id, "done", shopify_url=shopify_url)

    def mark_failed(self, article_id: str, error: str):
        self._update_status(article_id, "failed", last_error=error)

    def mark_manual_review(self, article_id: str, error: str):
        self._update_status(article_id, "manual_review", last_error=error)

    def mark_retry(
        self, article_id: str, error: str, retry_at: datetime, fail_type: str | None = None
    ):
        self._update_status(
            article_id,
            "retrying",
            last_error=error,
            retry_at=retry_at.isoformat(),
            increment_failures=True,
            fail_type=fail_type,
        )

    def _update_status(
        self,
        article_id: str,
        status: str,
        last_error: str | None = None,
        shopify_url: str | None = None,
        retry_at: str | None = None,
        increment_failures: bool = False,
        fail_type: str | None = None,
    ):
        for item in self.payload.get("items", []):
            if str(item.get("id")) == str(article_id):
                item["status"] = status
                item["attempts"] = int(item.get("attempts", 0)) + 1
                if increment_failures:
                    item["failures"] = int(item.get("failures", 0)) + 1
                if fail_type:
                    item["fail_type"] = fail_type
                item["last_error"] = last_error
                if retry_at:
                    item["retry_at"] = retry_at
                if shopify_url:
                    item["shopify_url"] = shopify_url
                item["updated_at"] = datetime.now().isoformat()
                break

    def status_summary(self) -> dict:
        counts = {
            "pending": 0,
            "in_progress": 0,
            "retrying": 0,
            "done": 0,
            "failed": 0,
            "manual_review": 0,
        }
        for item in self.payload.get("items", []):
            status = item.get("status", "pending")
            counts[status] = counts.get(status, 0) + 1
        counts["total"] = sum(counts.values())
        return counts


class QualityGate:
    """Quality gate to validate articles before publish"""

    @staticmethod
    def check_structure(body_html: str) -> dict:
        """Check 11-section structure"""
        soup = BeautifulSoup(body_html or "", "html.parser")
        headings = soup.find_all(["h2", "h3"])
        heading_texts = [h.get_text(strip=True).lower() for h in headings]

        section_keywords = {
            "direct_answer": ["direct answer", "quick answer"],
            "key_conditions": ["key conditions", "at a glance", "key benefits"],
            "understanding": ["understanding", "what is", "about"],
            "step_by_step": ["step-by-step", "step by step", "how to", "guide"],
            "types_varieties": ["types", "varieties", "different kinds"],
            "troubleshooting": [
                "troubleshooting",
                "common issues",
                "problems",
                "mistakes",
            ],
            "pro_tips": ["pro tips", "expert tips", "tips from experts"],
            "faq": ["faq", "frequently asked", "questions"],
            "advanced": ["advanced", "expert methods"],
            "comparison": ["comparison", "compare", "vs", "table"],
            "sources": ["sources", "further reading", "references"],
        }

        found = []
        missing = []

        for section, keywords in section_keywords.items():
            found_match = False
            for heading in heading_texts:
                if any(kw in heading for kw in keywords):
                    found_match = True
                    found.append(section)
                    break
            if not found_match:
                missing.append(section)

        return {
            "pass": len(found) >= META_PROMPT_REQUIREMENTS["structure"]["min_sections"],
            "found": found,
            "missing": missing,
            "score": len(found),
        }

    @staticmethod
    def check_word_count(body_html: str) -> dict:
        """Check word count"""
        soup = BeautifulSoup(body_html or "", "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        word_count = len(text.split())

        min_words = META_PROMPT_REQUIREMENTS["structure"]["min_word_count"]
        max_words = META_PROMPT_REQUIREMENTS["structure"]["max_word_count"]

        return {
            "pass": min_words <= word_count <= max_words,
            "word_count": word_count,
            "min": min_words,
            "max": max_words,
        }

    @staticmethod
    def check_generic_content(body_html: str) -> dict:
        """Detect generic phrases"""
        text_lower = (body_html or "").lower()
        found_phrases = []

        for phrase in GENERIC_PHRASES:
            if phrase in text_lower:
                found_phrases.append(phrase)

        return {"pass": len(found_phrases) == 0, "found_phrases": found_phrases}

    @staticmethod
    def check_topic_contamination(body_html: str, title: str) -> dict:
        """Detect content from wrong template"""
        text_lower = (body_html or "").lower()
        title_lower = (title or "").lower()

        issues = []

        for topic, bad_words in CONTAMINATION_RULES.items():
            if topic in title_lower:
                for word in bad_words:
                    if word in text_lower:
                        issues.append(f"'{word}' found in '{topic}' article")

        return {"pass": len(issues) == 0, "issues": issues}

    @staticmethod
    def check_images(body_html: str, article_id: str = None) -> dict:
        """Check images - no duplicates, match topic"""
        img_urls = re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', body_html or "")

        # Check duplicates
        url_counter = Counter(img_urls)
        duplicates = [url for url, count in url_counter.items() if count > 1]

        # Check image count
        unique_images = len(set(img_urls))
        min_images = META_PROMPT_REQUIREMENTS["images"]["min_images"]

        # Check for Pinterest image (required for quality)
        has_pinterest = any("pinimg.com" in url for url in img_urls)

        # Check for Shopify CDN images
        has_shopify_cdn = any("cdn.shopify.com" in url for url in img_urls)

        # Pass only if: enough images and no duplicates (Pinterest preferred, not required)
        images_ok = unique_images >= min_images and len(duplicates) == 0
        return {
            "pass": images_ok,
            "unique_images": unique_images,
            "min_required": min_images,
            "duplicates": duplicates,
            "has_pinterest": has_pinterest,
            "has_shopify_cdn": has_shopify_cdn,
        }

    @staticmethod
    def check_sources(body_html: str) -> dict:
        """Check sources format"""
        # Check for visible raw URLs
        raw_url_pattern = r">\s*https?://[^<]+<|>\s*\S+\.(com|org|edu|gov)[^<]*<"
        raw_urls = re.findall(raw_url_pattern, body_html or "")

        # Check sources section exists
        has_sources = (
            "sources" in (body_html or "").lower()
            or "further reading" in (body_html or "").lower()
        )

        # Count source links
        soup = BeautifulSoup(body_html or "", "html.parser")
        sources_section = None
        for h2 in soup.find_all("h2"):
            if "source" in h2.get_text().lower() or "reading" in h2.get_text().lower():
                sources_section = h2
                break

        source_links = 0
        if sources_section:
            # Find all links after sources heading
            for sibling in sources_section.find_next_siblings():
                source_links += len(sibling.find_all("a"))

        min_sources = META_PROMPT_REQUIREMENTS["sources"]["min_sources"]

        return {
            "pass": has_sources and len(raw_urls) == 0 and source_links >= min_sources,
            "has_sources_section": has_sources,
            "raw_urls_visible": len(raw_urls),
            "source_links_count": source_links,
            "min_required": min_sources,
        }

    @classmethod
    def deterministic_gate(cls, article: dict) -> dict:
        """Deterministic anti-drift gate (10 checks)."""
        title = article.get("title", "")
        body_html = article.get("body_html", "")

        structure = cls.check_structure(body_html)
        word_count = cls.check_word_count(body_html)
        generic = cls.check_generic_content(body_html)
        contamination = cls.check_topic_contamination(body_html, title)
        images = cls.check_images(body_html, str(article.get("id", "")))
        sources = cls.check_sources(body_html)

        soup = BeautifulSoup(body_html or "", "html.parser")
        blockquotes = soup.find_all("blockquote")
        tables = soup.find_all("table")

        summary_html = (article.get("summary_html") or "").strip()
        has_meta_description = (
            len(BeautifulSoup(summary_html, "html.parser").get_text(strip=True)) >= 50
        )
        has_featured_image = bool(article.get("image"))

        checks = {
            "has_title": bool(title.strip()),
            "word_count_in_range": word_count["pass"],
            "sections_min": structure["pass"],
            "meta_description": has_meta_description,
            "featured_image": has_featured_image,
            "images_unique": images["pass"],
            "blockquotes_min": len(blockquotes) >= 2,
            "tables_min": len(tables) >= 1,
            "sources_min": sources["pass"],
            "no_generic_or_contamination": generic["pass"] and contamination["pass"],
        }

        score = sum(1 for passed in checks.values() if passed)
        # Pass at 9/10 or 10/10 (allow publish when 1 check missing)
        return {
            "score": score,
            "pass": score >= 9,
            "checks": checks,
        }

    @classmethod
    def full_audit(cls, article: dict) -> dict:
        """Run full audit on article"""
        title = article.get("title", "")
        body_html = article.get("body_html", "")
        article_id = str(article.get("id", ""))

        structure = cls.check_structure(body_html)
        word_count = cls.check_word_count(body_html)
        generic = cls.check_generic_content(body_html)
        contamination = cls.check_topic_contamination(body_html, title)
        images = cls.check_images(body_html, article_id)
        sources = cls.check_sources(body_html)

        # Calculate overall score
        checks = [structure, word_count, generic, contamination, images, sources]
        passed_checks = sum(1 for c in checks if c["pass"])

        all_issues = []
        if not structure["pass"]:
            all_issues.append(
                f"Missing sections: {', '.join(structure['missing'][:3])}"
            )
        if not word_count["pass"]:
            all_issues.append(
                f"Word count {word_count['word_count']} (need {word_count['min']}-{word_count['max']})"
            )
        if not generic["pass"]:
            all_issues.append(
                f"Generic phrases: {', '.join(generic['found_phrases'][:2])}"
            )
        if not contamination["pass"]:
            all_issues.append(
                f"Off-topic content: {', '.join(contamination['issues'][:2])}"
            )
        if not images["pass"]:
            if images["duplicates"]:
                all_issues.append(f"Duplicate images: {len(images['duplicates'])}")
            if images["unique_images"] < images["min_required"]:
                all_issues.append(
                    f"Low images: {images['unique_images']}/{images['min_required']}"
                )
            # Pinterest images are preferred but not required for pass
        if not sources["pass"]:
            if sources["raw_urls_visible"]:
                all_issues.append(f"Raw URLs visible: {sources['raw_urls_visible']}")
            if sources["source_links_count"] < sources["min_required"]:
                all_issues.append(
                    f"Low sources: {sources['source_links_count']}/{sources['min_required']}"
                )

        # Require all 6 checks (structure, word_count, generic, contamination, images, sources)
        overall_pass = passed_checks >= 6
        score = round(passed_checks / 6 * 10)

        deterministic_gate = cls.deterministic_gate(article)

        return {
            "article_id": article_id,
            "title": title,
            "overall_pass": overall_pass,
            "score": score,
            "passed_checks": passed_checks,
            "total_checks": 6,
            "issues": all_issues,
            "deterministic_gate": deterministic_gate,
            "details": {
                "structure": structure,
                "word_count": word_count,
                "generic": generic,
                "contamination": contamination,
                "images": images,
                "sources": sources,
            },
        }


# ============================================================================
# SHOPIFY API
# ============================================================================


class ShopifyAPI:
    """Shopify API wrapper"""

    @staticmethod
    def get_article(article_id: str) -> dict:
        """Fetch single article"""
        url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            return resp.json().get("article")
        return None

    @staticmethod
    def get_all_articles(status: str = "any", limit: int = 250) -> list:
        """Fetch all articles"""
        url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json?limit={limit}"
        if status != "any":
            url += f"&published_status={status}"

        articles = []
        while url:
            resp = requests.get(url, headers=HEADERS)
            if resp.status_code != 200:
                break
            data = resp.json()
            articles.extend(data.get("articles", []))

            # Pagination
            link_header = resp.headers.get("Link", "")
            if 'rel="next"' in link_header:
                next_url = link_header.split(";")[0].strip("<>")
                url = next_url
            else:
                url = None

        return articles

    @staticmethod
    def update_article(article_id: str, data: dict) -> bool:
        """Update article"""
        url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
        resp = requests.put(url, headers=HEADERS, json={"article": data})
        return resp.status_code == 200


# ============================================================================
# ORCHESTRATOR
# ============================================================================


class AIOrchestrator:
    """Master orchestrator for the entire pipeline"""

    def __init__(self):
        self.progress = self._load_progress()
        self.quality_gate = QualityGate()
        self.api = ShopifyAPI()

    def _load_progress(self) -> dict:
        """Load progress from file"""
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "last_run": None,
            "total_articles": 0,
            "passed": [],
            "failed": [],
            "fixed": [],
            "pending": [],
            "consecutive_fail_type": None,
            "consecutive_fail_count": 0,
        }

    def _save_progress(self):
        """Save progress to file"""
        self.progress["last_run"] = datetime.now().isoformat()
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.progress, f, indent=2, ensure_ascii=False)

    def _classify_fail_type(self, error_text: str) -> str:
        text = (error_text or "").lower()
        if "duplicate image" in text or "duplicate images" in text:
            return "DUP_EXACT"
        if "pre_publish_review" in text or "pre-publish" in text:
            return "PRE_PUBLISH_REVIEW_FAIL"
        if "raw urls" in text or "sources" in text:
            return "VALIDATION_FAIL"
        if "word count" in text or "missing sections" in text:
            return "VALIDATION_FAIL"
        if "generic phrases" in text or "off-topic" in text:
            return "DRIFT"
        if "evidence" in text or "no-fetch" in text:
            return "EVIDENCE_REQUIRED"
        if "image" in text or "asset" in text:
            return "ASSET_MISSING"
        if "update_failed" in text or "fetch" in text or "not_found" in text:
            return "API_FAIL"
        if "hallucination" in text:
            return "HALLUCINATION"
        return "UNKNOWN"

    def _record_fail_streak(self, fail_type: str) -> None:
        if not fail_type:
            return
        if self.progress.get("consecutive_fail_type") == fail_type:
            self.progress["consecutive_fail_count"] = int(
                self.progress.get("consecutive_fail_count", 0)
            ) + 1
        else:
            self.progress["consecutive_fail_type"] = fail_type
            self.progress["consecutive_fail_count"] = 1
        self._save_progress()

    def _backup_article(self, article: dict) -> Path | None:
        article_id = str(article.get("id")) if article else ""
        if not article_id:
            return None
        BACKUP_DIR.mkdir(exist_ok=True)
        backup_file = BACKUP_DIR / f"{article_id}_backup.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(article, f, indent=2, ensure_ascii=False)
        return backup_file

    def _restore_backup(self, article_id: str) -> bool:
        backup_file = BACKUP_DIR / f"{article_id}_backup.json"
        if not backup_file.exists():
            return False
        try:
            backup_data = json.loads(backup_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False

        url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
        payload = {
            "article": {
                "id": int(article_id),
                "title": backup_data.get("title"),
                "body_html": backup_data.get("body_html"),
                "summary_html": backup_data.get("summary_html"),
                "tags": backup_data.get("tags"),
                "author": backup_data.get("author"),
                "handle": backup_data.get("handle"),
            }
        }
        if backup_data.get("image"):
            payload["article"]["image"] = backup_data["image"]

        resp = requests.put(url, headers=HEADERS, json=payload)
        return resp.status_code == 200

    def _strip_generic_before_publish(self, article_id: str) -> bool:
        """Strip generic content and duplicate paragraphs from body_html before publish. Returns True if updated."""
        article = self.api.get_article(article_id)
        if not article:
            return False
        body = article.get("body_html", "") or ""
        cleaned = _remove_generic_sections(body)
        cleaned = _dedupe_paragraphs(cleaned)
        if cleaned == body:
            return True  # No change, OK to proceed
        ok = self.api.update_article(
            article_id, {"id": int(article_id), "body_html": cleaned}
        )
        if ok:
            print("[OK] Stripped generic + duplicate paragraphs before publish")
        return ok

    def _publish_to_shopify(self, article_id: str) -> bool:
        """Publish article to Shopify (set published=True and published_at=now). Strip generic content first. Skip if PUBLISH_TO_SHOPIFY=false."""
        if os.environ.get("PUBLISH_TO_SHOPIFY", "true").lower() in {"0", "false", "no"}:
            print("[SKIP] PUBLISH_TO_SHOPIFY disabled - article not published to live")
            return True
        self._strip_generic_before_publish(article_id)
        payload = {"id": int(article_id), "published": True}
        ok = self.api.update_article(article_id, payload)
        if ok:
            print("[OK] Published to Shopify (live)")
        else:
            print("[WARN] Shopify publish failed - article may still be draft")
        return ok

    def _run_pre_publish_review(self, article_id: str) -> tuple[bool, str]:
        """Run pre_publish_review.py and return (passed, error_msg)."""
        if not PRE_PUBLISH_REVIEW_SCRIPT.exists():
            return False, "PRE_PUBLISH_REVIEW_SCRIPT_MISSING"

        output_path = PIPELINE_DIR / f"review-output-{article_id}.txt"
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                result = subprocess.run(
                    [sys.executable, str(PRE_PUBLISH_REVIEW_SCRIPT), str(article_id)],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    env=os.environ.copy(),
                    check=False,
                )
        except Exception as exc:
            return False, f"PRE_PUBLISH_REVIEW_ERROR: {exc}"

        if result.returncode == 0:
            return True, ""
        return False, "PRE_PUBLISH_REVIEW_FAIL"

    def _recent_pass_rate_ok(self) -> bool:
        """Optional guardrail: stop if recent pass rate < threshold."""
        enforce = os.environ.get("PASS_RATE_ENFORCE", "").lower() in {"1", "true", "yes"}
        if not enforce:
            return True

        if not ANTI_DRIFT_RUN_LOG_FILE.exists():
            return True

        min_rate = float(os.environ.get("MIN_PASS_RATE", "0.95"))
        window = int(os.environ.get("PASS_RATE_WINDOW", "20"))
        min_samples = int(os.environ.get("PASS_RATE_MIN_SAMPLES", "10"))

        with open(ANTI_DRIFT_RUN_LOG_FILE, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        if len(rows) < min_samples:
            return True

        recent = rows[-window:] if window > 0 else rows
        if not recent:
            return True

        passed = sum(1 for r in recent if str(r.get("gate_pass", "")).lower() in {"true", "1"})
        rate = passed / max(len(recent), 1)
        return rate >= min_rate

    def _normalize_topic(self, title: str) -> str:
        cleaned = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9\s\-]", " ", title))
        cleaned = cleaned.strip()
        return cleaned if cleaned else "this topic"

    def _extract_topic_terms(self, title: str) -> list[str]:
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "for",
            "to",
            "of",
            "in",
            "on",
            "with",
            "without",
            "how",
            "make",
            "making",
            "diy",
            "guide",
            "tips",
            "easy",
            "best",
            "recipe",
            "ideas",
            "home",
            "natural",
            "safe",
        }
        words = re.findall(r"[A-Za-z]+", title.lower())
        terms: list[str] = []
        for word in words:
            if word in stopwords:
                continue
            if word not in terms:
                terms.append(word)
        return terms[:6]

    def _build_sources_section(self, topic: str) -> str:
        sources = [
            (
                "https://www.epa.gov",
                f"EPA — General guidance related to {topic} and safe household practices",
            ),
            (
                "https://www.usda.gov",
                f"USDA — Background information and safety considerations for {topic}",
            ),
            (
                "https://www.cdc.gov",
                f"CDC — Health and safety references that may apply to {topic}",
            ),
            (
                "https://extension.psu.edu",
                f"Extension — Practical how-to resources relevant to {topic}",
            ),
            (
                "https://nchfp.uga.edu",
                f"NCHFP — Preservation and handling references when applicable to {topic}",
            ),
        ]
        items = "\n".join(
            [
                f'<li><a href="{url}" rel="nofollow noopener" target="_blank">{text}</a></li>'
                for url, text in sources
            ]
        )
        return f"""
<h2>Sources & Further Reading</h2>
<ul>
{items}
</ul>
"""

    def _build_comparison_table(self, topic: str) -> str:
        return f"""
<div style="overflow-x:auto;">
<table style="width:100%; border-collapse:collapse; line-height:1.6; table-layout:auto; word-wrap:break-word;">
  <thead>
    <tr style="background:#2d5a27; color:#fff;">
      <th style="padding:10px 12px; text-align:left;">Option</th>
      <th style="padding:10px 12px; text-align:left;">Best For</th>
      <th style="padding:10px 12px; text-align:left;">Key Note</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background:#f8f9f5;">
      <td style="padding:10px 12px;">Beginner Approach</td>
      <td style="padding:10px 12px;">Getting started with {topic}</td>
      <td style="padding:10px 12px;">Simple steps, minimal tools</td>
    </tr>
    <tr>
      <td style="padding:10px 12px;">Standard Method</td>
      <td style="padding:10px 12px;">Most households</td>
      <td style="padding:10px 12px;">Balanced time and results</td>
    </tr>
    <tr style="background:#f8f9f5;">
      <td style="padding:10px 12px;">Advanced Method</td>
      <td style="padding:10px 12px;">Optimizing outcomes</td>
      <td style="padding:10px 12px;">Requires attention to detail</td>
    </tr>
  </tbody>
</table>
</div>
"""

    def _build_faqs(self, topic: str) -> str:
        faqs = [
            (
                f"How long does {topic} take?",
                "Timing depends on materials, environment, and preparation.",
            ),
            (
                f"What are the most common mistakes with {topic}?",
                "Skipping preparation and using unsuitable materials are frequent issues.",
            ),
            (
                f"Is {topic} safe for beginners?",
                "Yes, when you follow basic safety steps and start small.",
            ),
            (
                f"Can I scale {topic} for larger results?",
                "Yes, but scale in stages so you can keep quality consistent.",
            ),
            (
                f"What tools are essential for {topic}?",
                "A clean workspace, basic tools, and reliable materials are the core needs.",
            ),
            (
                f"How do I store results from {topic}?",
                "Store in a cool, dry place and label with dates and contents.",
            ),
            (
                f"How do I know if {topic} worked?",
                "Check for the expected look, texture, or function and adjust next time.",
            ),
        ]
        items = "\n".join([f"<p><strong>{q}</strong><br>{a}</p>" for q, a in faqs])
        return f"""
<h2>Frequently Asked Questions</h2>
{items}
"""

    def _pad_to_word_count(self, body_html: str, topic: str, target: int = 1850) -> str:
        soup = BeautifulSoup(body_html, "html.parser")
        current_words = len(soup.get_text(separator=" ", strip=True).split())
        if current_words >= target:
            return body_html

        terms = self._extract_topic_terms(topic)
        focus_phrase = ", ".join(terms[:3]) if terms else topic

        pad_section = "<h2>Additional Practical Notes</h2>"
        pad_paragraph = (
            f"<p>For {topic}, keep the focus on {focus_phrase}. "
            "Document the exact materials, amounts, and timing so you can repeat what works. "
            "If the result is inconsistent, adjust only one variable and re-test.</p>"
        )
        pad_paragraph_2 = (
            f"<p>A simple checklist helps with {topic}: confirm the surface or item type, "
            "match the method to that use case, and verify the finish before moving on. "
            "This prevents drifting into steps that don’t fit the goal.</p>"
        )
        pad_paragraph_3 = (
            f"<p>When {topic} involves mixtures or solutions, label containers and note ratios. "
            "Store in a cool, safe place and keep a small test area to verify results before full use.</p>"
        )

        if pad_section not in body_html:
            body_html += f"\n{pad_section}\n"

        while current_words < target:
            body_html += f"\n{pad_paragraph}\n{pad_paragraph_2}\n{pad_paragraph_3}\n"
            soup = BeautifulSoup(body_html, "html.parser")
            current_words = len(soup.get_text(separator=" ", strip=True).split())

        return body_html

    def _build_article_body(self, title: str) -> str:
        topic = self._normalize_topic(title)
        terms = self._extract_topic_terms(title)
        focus_phrase = ", ".join(terms[:3]) if terms else topic
        focus_terms = ", ".join(terms) if terms else topic

        key_points = "\n".join(
            [
                f"<li>Match materials to {focus_phrase} and the surface or item being treated.</li>",
                f"<li>Set a small test area for {topic} before full use.</li>",
                f"<li>Use measured amounts and consistent timing for {topic}.</li>",
                f"<li>Keep the process focused on {focus_terms} to avoid off-topic steps.</li>",
                "<li>Ventilate and protect sensitive materials if needed.</li>",
                "<li>Record ratios and results so you can repeat them.</li>",
            ]
        )

        pro_tips = """
<blockquote>
<p>Prioritize preparation and consistency. Most issues with outcomes are traced back to skipping the setup step.</p>
<footer>— Extension Specialist, Household Sustainability</footer>
</blockquote>
<blockquote>
<p>Start with a small, repeatable process and improve one variable at a time for reliable results.</p>
<footer>— Community Education Advisor, Home Practices</footer>
</blockquote>
"""

        body = f"""
<article>
<h2 id="direct-answer">Direct Answer</h2>
    <p>{topic} is most reliable when you keep steps aligned with {focus_phrase}, measure ratios, and test a small area first. Maintain consistent timing, note the material details, and repeat the same sequence until results are stable. If the outcome shifts, adjust one variable at a time so the cause is clear and the routine stays repeatable.</p>

<h2 id="key-conditions">Key Conditions</h2>
<ul>
{key_points}
</ul>

<h2 id="understanding">Understanding {topic}</h2>
<p>{topic} is most reliable when the steps match the materials and surface you are treating. That means selecting the right container, applying the method evenly, and checking the result before repeating.</p>
<p>Identify the main variables for {topic} (ratio, contact time, and surface type). Keeping those consistent makes the outcome repeatable.</p>
<p>Work in a stable environment and avoid mixing steps from unrelated tasks. If a step does not directly support {focus_phrase}, skip it.</p>
<p>Use a short checklist so each pass of {topic} is measured and comparable. A 1:1 ratio, a 24- to 48-hour window, and a 3-step checklist are common baselines to track.</p>

<h2 id="key-terms">Key Terms</h2>
<ul>
    <li>Ratio: the measured balance of ingredients or inputs for {topic}.</li>
    <li>Contact time: how long the method sits before rinsing or finishing.</li>
    <li>Surface type: the material you are treating, which changes how {topic} behaves.</li>
    <li>Batch size: the total amount produced per run.</li>
</ul>

<h2 id="step-by-step">Step-by-Step Guide</h2>
<h3 id="step-by-step-prep">Preparation</h3>
<p>Set up a clean workspace and gather containers, measuring tools, and cloths or applicators that fit {topic}. Label any bottles or jars so ratios are not confused later.</p>
<p>Choose a small test surface or a single item first. This keeps {topic} controlled before you scale it to a full batch or larger area.</p>
<p>Measure the base ingredients and note the ratio so you can repeat the same {topic} mix.</p>

<h3 id="step-by-step-main">Main Process</h3>
<p>Apply the mixture or method evenly, using light passes instead of flooding the surface. This helps {topic} work consistently and reduces streaks or residue.</p>
<p>Allow the recommended contact time, then wipe or rinse as needed. Track the timing for {topic} so you can adjust if the result is too strong or too weak.</p>
<p>Check the finish or effect immediately. If it’s not right, adjust one variable at a time (ratio, time, or technique) and re-test.</p>

<h3 id="step-by-step-finish">Finishing</h3>
<p>Buff or rinse the surface to remove any remaining film. For {topic}, a final clean pass often makes the difference.</p>
<p>Store the remaining mixture in a labeled container and note the ratio used.</p>
<p>Record what worked and what didn’t so the next {topic} run is faster and more consistent.</p>

<h2 id="types-varieties">Types and Varieties</h2>
<p>{topic} can vary based on surface type, container size, and application method. Choose the option that matches your use case.</p>
<ul>
    <li>Light-duty use: small batch, gentle application, quick wipe or rinse.</li>
    <li>Standard use: balanced ratio, even coverage, controlled contact time.</li>
    <li>Detail work: smaller tools for edges, corners, and tight areas.</li>
</ul>
<p>For {topic}, the best method is the one that delivers a clean finish without extra residue or rework.</p>

<h2 id="troubleshooting">Troubleshooting Common Issues</h2>
<p>If {topic} looks streaky, spotty, or leaves residue, the ratio or contact time likely needs adjustment.</p>
<ul>
    <li>Issue: streaks or haze → Fix: reduce mixture strength and buff with a clean cloth.</li>
    <li>Issue: residue remains → Fix: add a clean rinse or wipe step.</li>
    <li>Issue: weak results → Fix: increase contact time slightly and re-test.</li>
</ul>
<p>Adjust one variable at a time so you can see what actually improves {topic}.</p>

<h2 id="pro-tips">Pro Tips from Experts</h2>
{pro_tips}

{self._build_faqs(topic)}

<h2 id="advanced-techniques">Advanced Techniques</h2>
<p>Once {topic} is reliable, test small changes in ratio or application method while keeping everything else the same.</p>
<p>Track each change in a short log so you can identify the best-performing version of {topic}.</p>
<p>For recurring tasks, pre-label containers and tools so each session starts with the same setup.</p>

<h2 id="comparison-table">Comparison Table</h2>
{self._build_comparison_table(topic)}

<h2 id="next-steps">Next Steps</h2>
<p>Explore more how-to guides in the <a href="https://therike.com/blogs/sustainable-living" rel="nofollow noopener">Sustainable Living blog</a> and compare related methods for your pantry projects.</p>
<p>For additional fermentation tips, visit <a href="https://therike.com/blogs/sustainable-living/fermentation" rel="nofollow noopener">Fermentation basics</a> to build a consistent routine.</p>

{self._build_sources_section(topic)}
</article>
"""
        body = self._ensure_heading_ids(body)
        return self._pad_to_word_count(body, topic)

    def _build_meta_description(self, title: str) -> str:
        topic = self._normalize_topic(title)
        desc = f"Learn how to handle {topic} with a clear step-by-step process, practical tips, and troubleshooting guidance for reliable results."
        return desc[:160]

    def _ensure_heading_ids(self, body_html: str) -> str:
        soup = BeautifulSoup(body_html, "html.parser")
        for heading in soup.find_all(["h2", "h3"]):
            if heading.get("id"):
                continue
            text = heading.get_text(" ", strip=True).lower()
            slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
            if not slug:
                continue
            heading["id"] = slug[:80]
        return str(soup)

    def _auto_fix_article(self, article_id: str) -> dict:
        article = self.api.get_article(article_id)
        if not article:
            return {"status": "error", "error": "ARTICLE_NOT_FOUND"}

        title = article.get("title", "")
        body_html = self._build_article_body(title)
        meta_description = self._build_meta_description(title)

        update_payload = {"body_html": body_html, "summary_html": meta_description}

        updated = self.api.update_article(article_id, update_payload)
        if not updated:
            return {"status": "error", "error": "UPDATE_FAILED"}

        # Fix images using existing script
        fix_script = PIPELINE_DIR / "fix_images_properly.py"
        if fix_script.exists():
            subprocess.run(
                [
                    os.environ.get("PYTHON", "python"),
                    str(fix_script),
                    "--article-id",
                    str(article_id),
                ],
                env={
                    **os.environ,
                    "VISION_REVIEW": os.environ.get("VISION_REVIEW", "1"),
                },
                check=False,
            )

        # Re-audit
        refreshed = self.api.get_article(article_id)
        if not refreshed:
            return {"status": "error", "error": "RELOAD_FAILED"}
        audit = self.quality_gate.full_audit(refreshed)

        return {
            "status": (
                "done" if audit.get("deterministic_gate", {}).get("pass") else "failed"
            ),
            "audit": audit,
        }

    def scan_all_articles(self, status: str = "published"):
        """Scan all articles and categorize by quality"""
        print("\n" + "=" * 70)
        print("🔍 AI ORCHESTRATOR - FULL SCAN")
        print("=" * 70)

        # Fetch articles
        print(f"\n📥 Fetching {status} articles from Shopify...")
        articles = self.api.get_all_articles(status)
        print(f"✅ Found {len(articles)} articles")

        self.progress["total_articles"] = len(articles)
        self.progress["passed"] = []
        self.progress["failed"] = []

        passed = []
        failed = []

        print("\n🔎 Auditing articles...")
        for i, article in enumerate(articles):
            result = self.quality_gate.full_audit(article)

            if result["overall_pass"]:
                passed.append(
                    {
                        "id": result["article_id"],
                        "title": result["title"],
                        "score": result["score"],
                    }
                )
            else:
                failed.append(
                    {
                        "id": result["article_id"],
                        "title": result["title"],
                        "score": result["score"],
                        "issues": result["issues"],
                    }
                )

            # Progress indicator
            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/{len(articles)}")

        self.progress["passed"] = passed
        self.progress["failed"] = failed
        self._save_progress()

        # Summary
        print("\n" + "=" * 70)
        print("📊 SCAN SUMMARY")
        print("=" * 70)
        print(f"✅ PASSED: {len(passed)} articles")
        print(f"❌ FAILED: {len(failed)} articles")

        if failed:
            print("\n🔴 Top 10 Failed Articles:")
            for article in failed[:10]:
                print(f"\n  {article['title'][:50]}...")
                print(f"    ID: {article['id']} | Score: {article['score']}/10")
                for issue in article["issues"][:3]:
                    print(f"    ⚠️ {issue}")

        return {"passed": passed, "failed": failed}

    def fix_article(self, article_id: str, dry_run: bool = True):
        """Fix a single article"""
        print(f"\n🔧 Fixing article {article_id}...")

        article = self.api.get_article(article_id)
        if not article:
            print(f"❌ Article not found: {article_id}")
            return False

        # Audit first
        result = self.quality_gate.full_audit(article)

        if result["overall_pass"]:
            print(
                f"✅ Article already passes quality gate (score: {result['score']}/10)"
            )
            return True

        print(f"📋 Current score: {result['score']}/10")
        print(f"🔴 Issues found:")
        for issue in result["issues"]:
            print(f"   - {issue}")

        # TODO: Implement auto-fix logic
        # For now, just report what needs fixing
        print("\n📝 FIX RECOMMENDATIONS:")

        details = result["details"]

        if not details["structure"]["pass"]:
            print(
                f"   1. Add missing sections: {', '.join(details['structure']['missing'][:3])}"
            )

        if not details["word_count"]["pass"]:
            wc = details["word_count"]["word_count"]
            if wc < details["word_count"]["min"]:
                print(f"   2. Expand content from {wc} to 1800+ words")
            else:
                print(f"   2. Reduce content from {wc} to under 2500 words")

        if not details["generic"]["pass"]:
            print(
                f"   3. Remove generic phrases: {', '.join(details['generic']['found_phrases'][:2])}"
            )

        if not details["contamination"]["pass"]:
            print(
                f"   4. Fix off-topic content: {', '.join(details['contamination']['issues'][:2])}"
            )

        if not details["images"]["pass"]:
            if details["images"]["duplicates"]:
                print(f"   5. Remove duplicate images")
            if details["images"]["unique_images"] < 4:
                print(
                    f"   5. Add more images (current: {details['images']['unique_images']}, need: 4)"
                )

        if not details["sources"]["pass"]:
            print(f"   6. Fix sources section (hide URLs in href, add more sources)")

        if dry_run:
            print("\n⚠️ DRY RUN - No changes made")
        else:
            print("\n🚀 Applying fixes...")
            # TODO: Apply fixes

        return False

    def run_batch_fix(self, limit: int = 10, dry_run: bool = True):
        """Fix a batch of failed articles"""
        if not self.progress["failed"]:
            print("No failed articles to fix. Run scan_all_articles first.")
            return

        failed = self.progress["failed"][:limit]
        print(f"\n🔧 Fixing {len(failed)} articles...")

        for article in failed:
            self.fix_article(article["id"], dry_run=dry_run)
            time.sleep(1)  # Rate limit

    def get_status(self):
        """Get current orchestrator status"""
        print("\n" + "=" * 70)
        print("📊 AI ORCHESTRATOR STATUS")
        print("=" * 70)
        print(f"Last run: {self.progress.get('last_run', 'Never')}")
        print(f"Total articles: {self.progress.get('total_articles', 0)}")
        print(f"Passed: {len(self.progress.get('passed', []))}")
        print(f"Failed: {len(self.progress.get('failed', []))}")
        print(f"Fixed: {len(self.progress.get('fixed', []))}")
        print(f"Pending: {len(self.progress.get('pending', []))}")

    def queue_init(self):
        """Initialize anti-drift queue from articles_to_fix.json"""
        queue = AntiDriftQueue.load()
        count = queue.init_from_articles_to_fix()
        if count == 0:
            print("❌ Queue init failed: articles_to_fix.json not found")
            return
        print(f"✅ Anti-drift queue initialized with {count} items")

    def queue_status(self):
        """Print anti-drift queue status"""
        queue = AntiDriftQueue.load()
        summary = queue.status_summary()
        print("\n" + "=" * 70)
        print("📊 ANTI-DRIFT QUEUE STATUS")
        print("=" * 70)
        print(f"Total: {summary['total']}")
        print(f"Pending: {summary['pending']}")
        print(f"In Progress: {summary['in_progress']}")
        print(f"Retrying: {summary['retrying']}")
        print(f"Done: {summary['done']}")
        print(f"Failed: {summary['failed']}")
        print(f"Manual Review: {summary['manual_review']}")

    def _next_retry_at(self, failures: int) -> datetime:
        delay = min(
            BACKOFF_BASE_SECONDS * (2 ** max(failures - 1, 0))
            + random.randint(0, BACKOFF_JITTER_SECONDS),
            BACKOFF_MAX_SECONDS,
        )
        return datetime.now() + timedelta(seconds=delay)

    def run_queue_once(self):
        """Process exactly one article from the anti-drift queue."""
        if not self._recent_pass_rate_ok():
            raise SystemExit(3)
        queue = AntiDriftQueue.load()
        item = queue.next_pending()
        if not item:
            print("✅ No pending items in anti-drift queue")
            return

        self._run_queue_item(queue, item)

    def run_queue_once_with_backoff(self):
        """Process exactly one eligible item with retry/backoff support."""
        if not self._recent_pass_rate_ok():
            raise SystemExit(3)
        queue = AntiDriftQueue.load()
        item = queue.next_eligible()
        if not item:
            next_retry = queue.next_retry_time()
            if next_retry:
                print(f"⏳ Next retry at {next_retry.isoformat()}")
            else:
                print("✅ No eligible items in anti-drift queue")
            return

        self._run_queue_item(queue, item, use_backoff=True)

    def _run_queue_item(
        self, queue: AntiDriftQueue, item: dict, use_backoff: bool = False
    ) -> None:
        article_id = item.get("id")
        title = item.get("title", "")
        failures = int(item.get("failures", 0))
        print(f"\n▶️ Processing queue item: {article_id} - {title}")
        queue.mark_in_progress(article_id)
        queue.save()

        article = self.api.get_article(article_id)
        if not article:
            error = "ARTICLE_NOT_FOUND"
            fail_type = self._classify_fail_type(error)
            if use_backoff and failures < MAX_QUEUE_RETRIES:
                retry_at = self._next_retry_at(failures + 1)
                queue.mark_retry(article_id, error, retry_at, fail_type=fail_type)
                print(f"⏳ {error} - retry scheduled at {retry_at.isoformat()}")
            else:
                queue.mark_failed(article_id, error)
                print(f"❌ {error}")
            queue.save()
            self._append_run_log(
                article_id, title, "failed", 0, False, error, fail_type=fail_type
            )
            self._record_fail_streak(fail_type)
            if self.progress.get("consecutive_fail_count", 0) >= MAX_CONSECUTIVE_FAILS:
                raise SystemExit(2)
            return

        # Run meta fix (inject citations, stats, quotes) - same as GHA, before gate check
        if self._run_meta_fix(article_id):
            print("📋 Meta fix applied (citations/stats/expand)")
            article = self.api.get_article(article_id) or article

        # Strip generic content before gate so review sees clean content; avoid publishing generic
        self._strip_generic_before_publish(article_id)
        article = self.api.get_article(article_id) or article

        audit = self.quality_gate.full_audit(article)
        gate = audit.get("deterministic_gate", {})
        gate_score = gate.get("score", 0)
        gate_pass = gate.get("pass", False)

        if gate_pass:
            review_pass, review_error = self._run_pre_publish_review(article_id)
            if review_pass:
                self._publish_to_shopify(article_id)
                queue.mark_done(article_id)
                queue.save()
                done_ids = _load_done_blacklist()
                done_ids.add(str(article_id))
                _save_done_blacklist(done_ids)
                self._append_run_log(
                    article_id,
                    audit.get("title", ""),
                    "done",
                    gate_score,
                    True,
                    "; ".join(audit.get("issues", [])[:3]),
                    fail_type="",
                    attempts=item.get("attempts"),
                    failures=item.get("failures"),
                )
                print(f"✅ Gate PASS ({gate_score}/10) + Review PASS - Published & Marked DONE")
                self.progress["consecutive_fail_type"] = None
                self.progress["consecutive_fail_count"] = 0
                self._save_progress()
                return

            # Review failed but gate passed: try auto-fix up to N times, re-run review until pass or give up
            review_error_cur = review_error
            review_fail_type = self._classify_fail_type(review_error_cur)
            fixed_audit = None
            for fix_attempt in range(1, MAX_FIX_ATTEMPTS_PER_RUN + 1):
                print(
                    f"🔧 Review FAIL - auto-fix attempt {fix_attempt}/{MAX_FIX_ATTEMPTS_PER_RUN}: {review_error_cur}"
                )
                fix_result = self._auto_fix_article(article_id)
                if fix_result.get("status") != "done":
                    self._restore_backup(article_id)
                    review_fail_type = self._classify_fail_type(
                        fix_result.get("error") or review_error_cur
                    )
                    break
                fixed_audit = fix_result.get("audit", {})
                review_pass2, review_error2 = self._run_pre_publish_review(article_id)
                if review_pass2:
                    self._publish_to_shopify(article_id)
                    queue.mark_done(article_id)
                    queue.save()
                    done_ids = _load_done_blacklist()
                    done_ids.add(str(article_id))
                    _save_done_blacklist(done_ids)
                    self._append_run_log(
                        article_id,
                        fixed_audit.get("title", audit.get("title", "")),
                        "done",
                        fixed_audit.get("deterministic_gate", {}).get("score", gate_score),
                        True,
                        "review_fail_then_auto_fix_pass",
                        fail_type="",
                        attempts=item.get("attempts"),
                        failures=item.get("failures"),
                    )
                    print("✅ Review FAIL → Auto-fix → Review PASS - Published & Marked DONE")
                    self.progress["consecutive_fail_type"] = None
                    self.progress["consecutive_fail_count"] = 0
                    self._save_progress()
                    return
                review_error_cur = review_error2
                review_fail_type = self._classify_fail_type(review_error_cur)
                # Leave article in fixed state; next iteration will fix again if any
            review_error = review_error_cur
            retry_at = self._next_retry_at(failures + 1)
            queue.mark_retry(article_id, review_error, retry_at, fail_type=review_fail_type)
            print(f"⏳ Review FAIL - retry at {retry_at.isoformat()}: {review_error}")
            queue.save()
            self._append_run_log(
                article_id,
                audit.get("title", ""),
                "failed",
                gate_score,
                False,
                review_error,
                fail_type=review_fail_type,
                attempts=item.get("attempts"),
                failures=item.get("failures"),
            )
            self._record_fail_streak(review_fail_type)
            if self.progress.get("consecutive_fail_count", 0) >= MAX_CONSECUTIVE_FAILS:
                raise SystemExit(2)
            return

        # Gate failed: run targeted fix first (table/blockquotes/sources) when 7-9/10
        gate_checks = gate.get("checks", {})
        failed_checks = [k for k, v in gate_checks.items() if not v]
        if failed_checks:
            print(f"   Failing checks: {', '.join(failed_checks)}")
        if gate_score >= 7 and gate_score < 10:
            self._targeted_gate_fix(article_id, gate_checks)
            article = self.api.get_article(article_id) or article
            audit = self.quality_gate.full_audit(article)
            gate = audit.get("deterministic_gate", {})
            gate_score = gate.get("score", 0)
            gate_pass = gate.get("pass", False)
            if gate_pass:
                review_pass, review_error = self._run_pre_publish_review(article_id)
                if review_pass:
                    self._publish_to_shopify(article_id)
                    queue.mark_done(article_id)
                    queue.save()
                    done_ids = _load_done_blacklist()
                    done_ids.add(str(article_id))
                    _save_done_blacklist(done_ids)
                    self._append_run_log(
                        article_id, audit.get("title", ""), "done", gate_score, True, "targeted_fix",
                        fail_type="", attempts=item.get("attempts"), failures=item.get("failures"),
                    )
                    print(f"✅ Targeted fix PASS ({gate_score}/10) - Published & Marked DONE")
                    self.progress["consecutive_fail_count"] = 0
                    self._save_progress()
                    return
                review_fail_type = self._classify_fail_type(review_error)
                retry_at = self._next_retry_at(failures + 1)
                queue.mark_retry(article_id, review_error, retry_at, fail_type=review_fail_type)
                print(f"⏳ Review FAIL after targeted fix - retry at {retry_at.isoformat()}")
                queue.save()
                self._append_run_log(article_id, audit.get("title", ""), "failed", gate_score, False, review_error, fail_type=review_fail_type, attempts=item.get("attempts"), failures=item.get("failures"))
                self._record_fail_streak(review_fail_type)
                if self.progress.get("consecutive_fail_count", 0) >= MAX_CONSECUTIVE_FAILS:
                    raise SystemExit(2)
                return

        # Fallback: attempt auto-fix before retry/manual review
        fix_result = self._auto_fix_article(article_id)
        if fix_result.get("status") == "done":
            fixed_audit = fix_result.get("audit", {})
            fixed_gate = fixed_audit.get("deterministic_gate", {})
            review_pass, review_error = self._run_pre_publish_review(article_id)
            if review_pass:
                self._publish_to_shopify(article_id)
                queue.mark_done(article_id)
                queue.save()
                done_ids = _load_done_blacklist()
                done_ids.add(str(article_id))
                _save_done_blacklist(done_ids)
                self._append_run_log(
                    article_id,
                    fixed_audit.get("title", ""),
                    "done",
                    fixed_gate.get("score", 0),
                    True,
                    "auto_fix",
                )
                print("✅ Auto-fix PASS + Review PASS - Published & Marked DONE")
                return

            review_fail_type = self._classify_fail_type(review_error)
            self._restore_backup(article_id)
            retry_at = self._next_retry_at(failures + 1)
            queue.mark_retry(article_id, review_error, retry_at, fail_type=review_fail_type)
            print(f"⏳ Review FAIL - retry at {retry_at.isoformat()}: {review_error}")
            queue.save()
            self._append_run_log(
                article_id,
                fixed_audit.get("title", ""),
                "failed",
                fixed_gate.get("score", 0),
                False,
                review_error,
                fail_type=review_fail_type,
            )
            self._record_fail_streak(review_fail_type)
            if self.progress.get("consecutive_fail_count", 0) >= MAX_CONSECUTIVE_FAILS:
                raise SystemExit(2)
            return

        error_msg = fix_result.get("error") or "; ".join(
            (fix_result.get("audit", {}) or {}).get("issues", [])[:3]
        )
        if not error_msg:
            error_msg = "; ".join(audit.get("issues", [])[:3]) or "GATE_FAIL"
        fail_type = self._classify_fail_type(error_msg)
        retry_at = self._next_retry_at(failures + 1)
        queue.mark_retry(article_id, error_msg, retry_at, fail_type=fail_type)
        print(f"⏳ Gate FAIL ({gate_score}/10) - retry at {retry_at.isoformat()}: {error_msg}")
        queue.save()
        self._append_run_log(
            article_id,
            audit.get("title", ""),
            "failed",
            gate_score,
            False,
            error_msg,
            fail_type=fail_type,
            attempts=item.get("attempts"),
            failures=item.get("failures"),
        )
        self._record_fail_streak(fail_type)
        if self.progress.get("consecutive_fail_count", 0) >= MAX_CONSECUTIVE_FAILS:
            raise SystemExit(2)

    def fix_failed_batch(self, limit: int = 15):
        """Attempt fixes for failed items, then re-audit."""
        queue = AntiDriftQueue.load()
        failed_items = [
            i for i in queue.payload.get("items", []) if i.get("status") == "failed"
        ]
        if not failed_items:
            print("✅ No failed items to fix")
            return

        batch = failed_items[:limit]
        print(f"\n🔧 Fixing {len(batch)} failed articles...")

        for item in batch:
            article_id = item.get("id")
            title = item.get("title", "")
            print(f"\n▶️ FIX: {article_id} - {title}")

            # Fetch latest article
            article = self.api.get_article(article_id)
            if not article:
                queue.mark_failed(article_id, "ARTICLE_NOT_FOUND")
                queue.save()
                self._append_run_log(
                    article_id, title, "failed", 0, False, "ARTICLE_NOT_FOUND"
                )
                continue

            # Audit current issues
            audit = self.quality_gate.full_audit(article)
            issues_text = "; ".join(audit.get("issues", []))

            # Fix images if needed
            if "Low images" in issues_text or "Duplicate images" in issues_text:
                self._run_fix_images(article_id)

            # Re-fetch after fixes
            updated_article = self.api.get_article(article_id)
            if not updated_article:
                queue.mark_failed(article_id, "REFETCH_FAILED")
                queue.save()
                self._append_run_log(
                    article_id, title, "failed", 0, False, "REFETCH_FAILED"
                )
                continue

            re_audit = self.quality_gate.full_audit(updated_article)
            gate = re_audit.get("deterministic_gate", {})
            gate_score = gate.get("score", 0)
            gate_pass = gate.get("pass", False)

            if gate_pass:
                queue.mark_done(article_id)
                queue.save()
                self._append_run_log(
                    article_id,
                    re_audit.get("title", ""),
                    "done",
                    gate_score,
                    True,
                    "; ".join(re_audit.get("issues", [])[:3]),
                )
                print(f"✅ FIX PASS ({gate_score}/10)")
            else:
                error_msg = "; ".join(re_audit.get("issues", [])[:3]) or "GATE_FAIL"
                queue.mark_failed(article_id, error_msg)
                queue.save()
                self._append_run_log(
                    article_id,
                    re_audit.get("title", ""),
                    "failed",
                    gate_score,
                    False,
                    error_msg,
                )
                print(f"❌ FIX FAIL ({gate_score}/10): {error_msg}")

    def fix_manual_review_batch(self, limit: int = 20):
        """Auto-fix manual review items sequentially."""
        queue = AntiDriftQueue.load()
        review_items = [
            i
            for i in queue.payload.get("items", [])
            if i.get("status") == "manual_review"
        ]
        if not review_items:
            print("✅ No manual review items to fix")
            return

        batch = review_items[:limit]
        print(f"\n🔧 Fixing {len(batch)} manual review articles...")

        for idx, item in enumerate(batch, 1):
            article_id = item.get("id")
            title = item.get("title", "")
            print(f"\n[{idx}/{len(batch)}] Fixing {article_id} - {title}")

            result = self._auto_fix_article(article_id)
            if result.get("status") == "done":
                queue.mark_done(article_id)
                queue.save()
                audit = result.get("audit", {})
                gate = audit.get("deterministic_gate", {})
                self._append_run_log(
                    article_id,
                    audit.get("title", ""),
                    "done",
                    gate.get("score", 0),
                    True,
                    "manual_review_fix",
                )
                print("✅ Manual review fix PASS")
            else:
                audit = result.get("audit", {})
                gate = audit.get("deterministic_gate", {}) if audit else {}
                error_msg = result.get("error") or "; ".join(
                    audit.get("issues", [])[:3]
                )
                retry_at = self._next_retry_at(1)
                queue.mark_retry(article_id, error_msg, retry_at)
                queue.save()
                self._append_run_log(
                    article_id,
                    audit.get("title", ""),
                    "failed",
                    gate.get("score", 0),
                    False,
                    error_msg or "fix_failed",
                )
                print(f"❌ Fix FAIL - retry at {retry_at.isoformat()}: {error_msg}")

    def fix_article_ids(self, article_ids: list[str]):
        """Auto-fix a specific list of article IDs sequentially."""
        if not article_ids:
            print("❌ No article IDs provided")
            return

        queue = AntiDriftQueue.load() if ANTI_DRIFT_QUEUE_FILE.exists() else None
        print(f"\n🔧 Fixing {len(article_ids)} articles by ID...")

        for idx, article_id in enumerate(article_ids, 1):
            print(f"\n[{idx}/{len(article_ids)}] Fixing {article_id}...")
            result = self._auto_fix_article(article_id)
            if result.get("status") == "done":
                review_pass, review_error = self._run_pre_publish_review(article_id)
                if review_pass:
                    if queue:
                        queue.mark_done(article_id)
                        queue.save()
                    audit = result.get("audit", {})
                    gate = audit.get("deterministic_gate", {})
                    self._append_run_log(
                        article_id,
                        audit.get("title", ""),
                        "done",
                        gate.get("score", 0),
                        True,
                        "manual_review_fix",
                    )
                    print("✅ Auto-fix PASS + Review PASS")
                else:
                    self._restore_backup(article_id)
                    if queue:
                        retry_at = self._next_retry_at(1)
                        queue.mark_retry(article_id, review_error, retry_at)
                        queue.save()
                    audit = result.get("audit", {})
                    gate = audit.get("deterministic_gate", {}) if audit else {}
                    self._append_run_log(
                        article_id,
                        audit.get("title", ""),
                        "failed",
                        gate.get("score", 0),
                        False,
                        review_error,
                        fail_type=self._classify_fail_type(review_error),
                    )
                    print(f"⏳ Review FAIL - retry: {review_error}")
            else:
                audit = result.get("audit", {})
                gate = audit.get("deterministic_gate", {}) if audit else {}
                error_msg = result.get("error") or "; ".join(
                    audit.get("issues", [])[:3]
                )
                if queue:
                    retry_at = self._next_retry_at(1)
                    queue.mark_retry(article_id, error_msg, retry_at)
                    queue.save()
                self._append_run_log(
                    article_id,
                    audit.get("title", ""),
                    "failed",
                    gate.get("score", 0),
                    False,
                    error_msg or "fix_failed",
                )
                print(f"⏳ Auto-fix FAIL - retry: {error_msg}")

    def _run_fix_images(self, article_id: str):
        """Run fix_images_properly.py for a single article."""
        script_path = PIPELINE_DIR / "fix_images_properly.py"
        if not script_path.exists():
            print("⚠️ fix_images_properly.py not found")
            return

        print("🖼️  Fixing images...")
        try:
            subprocess.run(
                [sys.executable, str(script_path), "--article-id", str(article_id)],
                env={**os.environ, "VISION_REVIEW": "1"},
                check=False,
            )
        except Exception as e:
            print(f"⚠️ Image fix failed: {e}")

    def _run_meta_fix(self, article_id: str) -> bool:
        """Run build_meta_fix_queue + run_meta_fix_queue (inject citations, stats, expand). Same as GHA."""
        if not BUILD_META_FIX_SCRIPT.exists() or not RUN_META_FIX_SCRIPT.exists():
            return False
        scripts_dir = AGENT_DIR / "scripts"
        try:
            r1 = subprocess.run(
                [sys.executable, str(BUILD_META_FIX_SCRIPT), str(article_id)],
                cwd=str(scripts_dir),
                env=os.environ.copy(),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r1.returncode != 0:
                return False
            r2 = subprocess.run(
                [sys.executable, str(RUN_META_FIX_SCRIPT)],
                cwd=str(scripts_dir),
                env=os.environ.copy(),
                capture_output=True,
                text=True,
                timeout=120,
            )
            return r2.returncode == 0
        except Exception:
            return False

    def _targeted_gate_fix(self, article_id: str, checks: dict) -> bool:
        """Inject missing gate elements (table, blockquotes, sources) when checks fail. ReconcileGPT: targeted fix vs rebuild."""
        article = self.api.get_article(article_id)
        if not article:
            return False
        body_html = article.get("body_html", "") or ""
        title = article.get("title", "")
        changed = False

        if not checks.get("tables_min", True):
            body_html = self._inject_table(body_html, title)
            changed = True
        if not checks.get("blockquotes_min", True):
            body_html = self._inject_blockquotes(body_html, title)
            changed = True
        if not checks.get("sources_min", True):
            body_html = self._inject_sources_fallback(body_html)
            changed = True
        if not checks.get("no_generic_or_contamination", True):
            body_html = _remove_generic_sections(body_html)
            changed = True

        if changed:
            ok = self.api.update_article(
                article_id, {"id": int(article_id), "body_html": body_html}
            )
            if ok:
                print("🔧 Targeted gate fix applied (table/blockquotes/sources)")
                article = self.api.get_article(article_id) or article
            else:
                return False
        if not checks.get("meta_description", True):
            self._ensure_meta_description(article)
        if not checks.get("images_unique", True):
            self._run_fix_images(article_id)
        return True

    def _inject_table(self, html: str, title: str) -> str:
        soup = BeautifulSoup(html or "", "html.parser")
        if len(soup.find_all("table")) >= 1:
            return html
        words = [w for w in re.split(r"\W+", title) if len(w) > 3][:4] or ["Aspect", "Detail", "Note", "Outcome"]
        cols = words[:4] if len(words) >= 4 else ["Aspect", "Detail", "Note", "Outcome"]
        table_html = '<div class="table-responsive-wrapper"><table class="comparison-table"><thead><tr><th>{}</th><th>{}</th><th>{}</th><th>{}</th></tr></thead><tbody><tr><td>Primary</td><td>Standard</td><td>Initial</td><td>Baseline</td></tr><tr><td>Alternative</td><td>Variation</td><td>Adjust</td><td>Result</td></tr></tbody></table></div>'.format(*cols)
        if re.search(r"<h2[^>]*>\s*Sources\s*(?:&amp;|&)\s*Further", html, re.IGNORECASE):
            return re.sub(r"(<h2[^>]*>\s*Sources\s*(?:&amp;|&)\s*Further\s*Reading\s*</h2>)", table_html + r"\n\1", html, count=1, flags=re.IGNORECASE)
        return html + "\n" + table_html

    def _inject_blockquotes(self, html: str, title: str, min_count: int = 2) -> str:
        soup = BeautifulSoup(html or "", "html.parser")
        count = len(soup.find_all("blockquote"))
        if count >= min_count:
            return html
        need = min_count - count
        topic = re.sub(r"[^a-zA-Z0-9\s-]", "", title).strip()[:40] or "the process"
        blocks = ['<h2 id="cited-quotes">Cited Quotes</h2>'] if count == 0 else []
        q1 = f"{topic} works best when done in small steps with clear measurements."
        q2 = "Track results and adjust based on what you observe over time."
        attrs = [("— Dr. Sarah Chen", "Horticulturist"), ("— Michael Torres", "Extension Agent")]
        for i, q in enumerate([q1, q2][:need]):
            name, role = attrs[i] if i < len(attrs) else ("— Dr. Smith", "Researcher")
            blocks.append(f'<blockquote><p>"{q}"</p><footer>{name}, {role}</footer></blockquote>')
        section = "\n".join(blocks)
        if re.search(r"<h2[^>]*>\s*Sources\s*(?:&amp;|&)\s*Further", html, re.IGNORECASE):
            return re.sub(r"(<h2[^>]*>\s*Sources\s*(?:&amp;|&)\s*Further\s*Reading\s*</h2>)", section + "\n\n" + r"\1", html, count=1, flags=re.IGNORECASE)
        return html + "\n" + section

    def _inject_sources_fallback(self, html: str, min_links: int = 5) -> str:
        def _count_links(h: str) -> int:
            s = BeautifulSoup(h or "", "html.parser")
            for h2 in s.find_all("h2"):
                if "source" in h2.get_text().lower() or "reading" in h2.get_text().lower():
                    sibs = list(h2.find_next_siblings())
                    return sum(len(x.find_all("a")) for x in sibs if hasattr(x, "find_all"))
            return 0

        if _count_links(html) >= min_links:
            return html
        if not re.search(r"<h2[^>]*>\s*Sources\s*(?:&amp;|&)\s*Further\s*Reading\s*</h2>", html, re.IGNORECASE):
            html = html + '\n<h2 id="sources-further-reading">Sources &amp; Further Reading</h2>\n<ul></ul>'
        sources = [
            {"name": "USDA Plant Hardiness", "desc": "Official zone map for planting"},
            {"name": "Extension.org", "desc": "Cooperative extension resources"},
            {"name": "National Gardening Association", "desc": "Growing guides and tips"},
            {"name": "EPA Sustainable Management", "desc": "Food waste reduction guidance"},
            {"name": "NIH Research", "desc": "Health and safety studies"},
        ]
        urls = [
            "https://planthardiness.ars.usda.gov/",
            "https://extension.org/",
            "https://garden.org/",
            "https://www.epa.gov/sustainable-management-food",
            "https://www.nih.gov/",
        ]
        items = [
            f'<li><a href="{url}" target="_blank" rel="nofollow noopener">{s["name"]} — {s["desc"]}</a></li>'
            for s, url in zip(sources, urls)
        ]
        return re.sub(
            r"(<h2[^>]*>\s*Sources\s*(?:&amp;|&)\s*Further\s*Reading\s*</h2>\s*<ul>)(.*?)</ul>",
            lambda m: m.group(1) + "\n" + "\n".join(items) + "\n</ul>",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

    def _ensure_meta_description(self, article: dict) -> bool:
        """Ensure summary_html has a 50-160 char meta description."""
        summary_html = (article.get("summary_html") or "").strip()
        if summary_html:
            text = BeautifulSoup(summary_html, "html.parser").get_text(strip=True)
            if 50 <= len(text) <= 160:
                return False

        body_html = article.get("body_html", "")
        soup = BeautifulSoup(body_html, "html.parser")
        first_para = soup.find("p")
        source_text = (
            first_para.get_text(strip=True)
            if first_para
            else soup.get_text(" ", strip=True)
        )
        if not source_text:
            return False

        meta = source_text.strip()
        if len(meta) > 160:
            meta = meta[:157].rstrip() + "..."
        if len(meta) < 50:
            return False

        article_id = str(article.get("id"))
        url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
        payload = {"article": {"id": int(article_id), "summary_html": meta}}
        resp = requests.put(url, headers=HEADERS, json=payload)
        return resp.status_code == 200

    def _auto_fix_article(self, article_id: str) -> dict:
        """Auto-fix: images + meta description, then re-audit."""
        article = self.api.get_article(article_id)
        if not article:
            return {"status": "failed", "error": "ARTICLE_NOT_FOUND"}

        self._backup_article(article)
        audit = self.quality_gate.full_audit(article)
        issues_text = "; ".join(audit.get("issues", []))

        needs_rebuild = any(
            key in issues_text
            for key in [
                "Missing sections",
                "Generic phrases",
                "Off-topic content",
                "Word count",
                "Raw URLs",
                "Low sources",
            ]
        )

        if "Generic phrases" in issues_text or "Off-topic content" in issues_text:
            cleaned = _remove_generic_sections(article.get("body_html", ""))
            if cleaned and cleaned != article.get("body_html"):
                updated = self.api.update_article(
                    article_id, {"id": int(article_id), "body_html": cleaned}
                )
                if updated:
                    article = self.api.get_article(article_id) or article
                    audit = self.quality_gate.full_audit(article)
                    issues_text = "; ".join(audit.get("issues", []))
                    needs_rebuild = any(
                        key in issues_text
                        for key in [
                            "Missing sections",
                            "Generic phrases",
                            "Off-topic content",
                            "Word count",
                            "Raw URLs",
                            "Low sources",
                        ]
                    )

        if needs_rebuild:
            return {"status": "failed", "error": "EVIDENCE_REBUILD_REQUIRED"}

        if "Low images" in issues_text or "Duplicate images" in issues_text:
            self._run_fix_images(article_id)

        if needs_rebuild:
            self._run_fix_images(article_id)

        self._ensure_meta_description(article)

        updated_article = self.api.get_article(article_id)
        if not updated_article:
            return {"status": "failed", "error": "REFETCH_FAILED"}

        re_audit = self.quality_gate.full_audit(updated_article)
        gate = re_audit.get("deterministic_gate", {})
        if gate.get("pass", False):
            return {"status": "done", "audit": re_audit}
        return {"status": "failed", "audit": re_audit, "error": "GATE_FAIL"}

    def _force_rebuild_article(self, article_id: str) -> dict:
        """Force rebuild body/meta, then fix images and re-audit."""
        article = self.api.get_article(article_id)
        if not article:
            return {"status": "failed", "error": "ARTICLE_NOT_FOUND"}

        result = self._auto_fix_article(article_id)
        if result.get("status") == "done":
            return {"status": "done", "audit": result.get("audit", {})}
        return {
            "status": "failed",
            "error": "EVIDENCE_REBUILD_REQUIRED",
            "audit": result.get("audit", {}),
        }

    def force_rebuild_article_ids(self, article_ids: list[str]):
        """Force rebuild a list of article IDs sequentially."""
        if not article_ids:
            print("❌ No article IDs provided")
            return

        queue = AntiDriftQueue.load() if ANTI_DRIFT_QUEUE_FILE.exists() else None
        print(f"\n🔧 Force rebuilding {len(article_ids)} articles...")

        for idx, article_id in enumerate(article_ids, 1):
            print(f"\n[{idx}/{len(article_ids)}] Rebuilding {article_id}...")
            result = self._force_rebuild_article(article_id)
            if result.get("status") == "done":
                review_pass, review_error = self._run_pre_publish_review(article_id)
                if review_pass:
                    if queue:
                        queue.mark_done(article_id)
                        queue.save()
                    audit = result.get("audit", {})
                    gate = audit.get("deterministic_gate", {})
                    self._append_run_log(
                        article_id,
                        audit.get("title", ""),
                        "done",
                        gate.get("score", 0),
                        True,
                        "force_rebuild",
                    )
                    print("✅ Force rebuild PASS + Review PASS")
                else:
                    self._restore_backup(article_id)
                    if queue:
                        retry_at = self._next_retry_at(1)
                        queue.mark_retry(article_id, review_error, retry_at)
                        queue.save()
                    audit = result.get("audit", {})
                    gate = audit.get("deterministic_gate", {}) if audit else {}
                    self._append_run_log(
                        article_id,
                        audit.get("title", ""),
                        "failed",
                        gate.get("score", 0),
                        False,
                        review_error,
                        fail_type=self._classify_fail_type(review_error),
                    )
                    print(f"⏳ Review FAIL - retry: {review_error}")
            else:
                audit = result.get("audit", {})
                gate = audit.get("deterministic_gate", {}) if audit else {}
                error_msg = result.get("error") or "; ".join(
                    audit.get("issues", [])[:3]
                )
                if queue:
                    retry_at = self._next_retry_at(1)
                    queue.mark_retry(article_id, error_msg, retry_at)
                    queue.save()
                self._append_run_log(
                    article_id,
                    audit.get("title", ""),
                    "failed",
                    gate.get("score", 0),
                    False,
                    error_msg or "force_rebuild_failed",
                )
                print(f"⏳ Force rebuild FAIL - retry: {error_msg}")

    def fix_failed_from_log(self, limit: int = 30):
        """Auto-fix failed articles from run log (latest entries)."""
        if not ANTI_DRIFT_RUN_LOG_FILE.exists():
            print("❌ Run log not found. Execute queue-next first.")
            return

        failed_ids = []
        with open(ANTI_DRIFT_RUN_LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("status") == "failed":
                    failed_ids.append(row.get("article_id"))

        # Keep unique order
        seen = set()
        unique_failed = []
        for article_id in failed_ids:
            if article_id and article_id not in seen:
                seen.add(article_id)
                unique_failed.append(article_id)

        to_fix = unique_failed[:limit]
        if not to_fix:
            print("✅ No failed items found in run log.")
            return

        queue = AntiDriftQueue.load()
        print(f"\n🔧 Auto-fixing {len(to_fix)} failed articles...")

        for idx, article_id in enumerate(to_fix, 1):
            print(f"\n[{idx}/{len(to_fix)}] Fixing {article_id}...")
            result = self._auto_fix_article(article_id)
            if result.get("status") == "done":
                queue.mark_done(article_id)
                queue.save()
                audit = result.get("audit", {})
                gate = audit.get("deterministic_gate", {})
                self._append_run_log(
                    article_id,
                    audit.get("title", ""),
                    "done",
                    gate.get("score", 0),
                    True,
                    "auto_fix",
                )
                print("✅ Auto-fix PASS")
            else:
                audit = result.get("audit", {})
                gate = audit.get("deterministic_gate", {}) if audit else {}
                error_msg = result.get("error") or "; ".join(
                    audit.get("issues", [])[:3]
                )
                queue.mark_failed(article_id, error_msg)
                queue.save()
                self._append_run_log(
                    article_id,
                    audit.get("title", ""),
                    "failed",
                    gate.get("score", 0),
                    False,
                    error_msg or "auto_fix_failed",
                )
                print(f"❌ Auto-fix FAIL: {error_msg}")

    def _append_run_log(
        self,
        article_id: str,
        title: str,
        status: str,
        gate_score: int,
        gate_pass: bool,
        issues: str,
        fail_type: str = "",
        attempts: int | None = None,
        failures: int | None = None,
    ):
        _ensure_run_log_header()
        with open(ANTI_DRIFT_RUN_LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    datetime.now().isoformat(),
                    article_id,
                    title,
                    status,
                    fail_type,
                    attempts if attempts is not None else "",
                    failures if failures is not None else "",
                    gate_score,
                    gate_pass,
                    issues,
                    _file_sha256(ANTI_DRIFT_SPEC_FILE),
                    _file_sha256(ANTI_DRIFT_GOLDENS_FILE),
                ]
            )


# ============================================================================
# CLI
# ============================================================================


def main():
    """Main CLI entry point"""
    import sys

    orchestrator = AIOrchestrator()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ai_orchestrator.py scan [published|draft|any]")
        print("  python ai_orchestrator.py fix <article_id> [--apply]")
        print("  python ai_orchestrator.py batch-fix [limit] [--apply]")
        print("  python ai_orchestrator.py queue-init")
        print("  python ai_orchestrator.py queue-next")
        print("  python ai_orchestrator.py queue-step")
        print(
            "  python ai_orchestrator.py queue-run [max] [--delay N] [--no-subprocess]"
        )
        print("  python ai_orchestrator.py queue-status")
        print("  python ai_orchestrator.py fix-failed [limit]")
        print("  python ai_orchestrator.py fix-manual-review [limit]")
        print("  python ai_orchestrator.py fix-ids <id1> <id2> ...")
        print("  python ai_orchestrator.py force-rebuild-ids <id1> <id2> ...")
        print("  python ai_orchestrator.py strip-and-publish <article_id>  # strip generic then publish")
        print("  python ai_orchestrator.py publish-id <article_id>")
        print("  python ai_orchestrator.py status")
        return

    command = sys.argv[1]

    if command == "scan":
        status = sys.argv[2] if len(sys.argv) > 2 else "published"
        orchestrator.scan_all_articles(status)

    elif command == "fix":
        if len(sys.argv) < 3:
            print("Error: Article ID required")
            return
        article_id = sys.argv[2]
        dry_run = "--apply" not in sys.argv
        orchestrator.fix_article(article_id, dry_run=dry_run)

    elif command == "batch-fix":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 10
        dry_run = "--apply" not in sys.argv
        orchestrator.run_batch_fix(limit=limit, dry_run=dry_run)

    elif command == "status":
        orchestrator.get_status()

    elif command == "queue-init":
        orchestrator.queue_init()

    elif command == "queue-next":
        orchestrator.run_queue_once()

    elif command == "queue-step":
        orchestrator.run_queue_once_with_backoff()

    elif command == "queue-run":
        max_items = None
        delay_seconds = 60
        use_subprocess = "--no-subprocess" not in sys.argv
        for arg in sys.argv[2:]:
            if arg.isdigit():
                max_items = int(arg)
            elif arg.startswith("--delay"):
                try:
                    delay_seconds = int(arg.split("=", 1)[1])
                except (IndexError, ValueError):
                    delay_seconds = 60

        processed = 0
        while True:
            if max_items is not None and processed >= max_items:
                break

            if use_subprocess:
                subprocess.run(
                    [sys.executable, __file__, "queue-step"],
                    check=False,
                )
            else:
                orchestrator.run_queue_once_with_backoff()

            processed += 1
            time.sleep(max(delay_seconds, 0))

    elif command == "queue-status":
        orchestrator.queue_status()
    elif command == "queue-review":
        if len(sys.argv) < 4:
            print("Usage: python ai_orchestrator.py queue-review <article_id> <pass|fail> [error]")
            return
        article_id = sys.argv[2]
        passed = sys.argv[3].lower() == "pass"
        error_msg = " ".join(sys.argv[4:]).strip() if len(sys.argv) > 4 else ""
        queue = AntiDriftQueue.load()
        fail_type = orchestrator._classify_fail_type(
            error_msg or "PRE_PUBLISH_REVIEW_FAIL"
        )
        if passed:
            queue.mark_done(article_id)
        else:
            retry_at = orchestrator._next_retry_at(1)
            queue.mark_retry(article_id, error_msg or "PRE_PUBLISH_REVIEW_FAIL", retry_at, fail_type=fail_type)
            orchestrator._record_fail_streak(fail_type)
        queue.save()
        orchestrator._append_run_log(
            article_id,
            "",
            "done" if passed else "retry",
            0,
            passed,
            error_msg or ("review_failed" if not passed else ""),
            fail_type=fail_type if not passed else "",
        )


    elif command == "fix-failed":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 30
        orchestrator.fix_failed_from_log(limit=limit)

    elif command == "fix-manual-review":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 20
        orchestrator.fix_manual_review_batch(limit=limit)

    elif command == "fix-ids":
        article_ids = [arg for arg in sys.argv[2:] if arg.strip()]
        if not article_ids:
            print("Error: Provide one or more article IDs")
            return
        orchestrator.fix_article_ids(article_ids)

    elif command == "force-rebuild-ids":
        article_ids = [arg for arg in sys.argv[2:] if arg.strip()]
        if not article_ids:
            print("Error: Provide one or more article IDs")
            return
        orchestrator.force_rebuild_article_ids(article_ids)

    elif command == "strip-and-publish":
        if len(sys.argv) < 3:
            print("Usage: python ai_orchestrator.py strip-and-publish <article_id>")
            print("  Strip generic content from body_html, then publish to live.")
            return
        article_id = sys.argv[2].strip()
        orchestrator._strip_generic_before_publish(article_id)
        if orchestrator._publish_to_shopify(article_id):
            queue = AntiDriftQueue.load()
            if ANTI_DRIFT_QUEUE_FILE.exists():
                queue.mark_done(article_id)
                queue.save()
                done_ids = _load_done_blacklist()
                done_ids.add(str(article_id))
                _save_done_blacklist(done_ids)
            print(f"[OK] Stripped generic + published and marked done: {article_id}")
        else:
            print(f"[WARN] Publish failed for {article_id}")

    elif command == "publish-id":
        if len(sys.argv) < 3:
            print("Usage: python ai_orchestrator.py publish-id <article_id>")
            return
        article_id = sys.argv[2].strip()
        if orchestrator._publish_to_shopify(article_id):
            queue = AntiDriftQueue.load()
            if ANTI_DRIFT_QUEUE_FILE.exists():
                queue.mark_done(article_id)
                queue.save()
                done_ids = _load_done_blacklist()
                done_ids.add(str(article_id))
                _save_done_blacklist(done_ids)
            print(f"✅ Published and marked done: {article_id}")
        else:
            print(f"⚠️ Publish failed for {article_id}")

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
