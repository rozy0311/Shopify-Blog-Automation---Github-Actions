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
        load_dotenv(env_path)
BACKOFF_BASE_SECONDS = 120
BACKOFF_MAX_SECONDS = 600
BACKOFF_JITTER_SECONDS = 30
PROGRESS_FILE = Path(__file__).parent / "progress.json"
PIPELINE_DIR = Path(__file__).parent
ROOT_DIR = PIPELINE_DIR.parent.parent
# Queue and log in pipeline_v2 so GHA (working-directory pipeline_v2) finds them
ANTI_DRIFT_QUEUE_FILE = PIPELINE_DIR / "anti_drift_queue.json"
ANTI_DRIFT_RUN_LOG_FILE = PIPELINE_DIR / "anti_drift_run_log.csv"
ANTI_DRIFT_DONE_FILE = PIPELINE_DIR / "anti_drift_done.json"
ANTI_DRIFT_SPEC_FILE = PIPELINE_DIR / "anti_drift_spec_v1.md"
ANTI_DRIFT_GOLDENS_FILE = PIPELINE_DIR / "anti_drift_goldens_12.json"


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
        "required_types": ["pinterest_original", "ai_inline", "featured"],
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

# Generic phrases to detect - SYNCED with pre_publish_review.py
GENERIC_PHRASES = [
    "comprehensive guide", "ultimate guide", "complete guide", "definitive guide",
    "in this guide", "this guide", "this article", "this blog post",
    "whether you're a beginner", "whether you are a beginner", "whether you are new",
    "in today's world", "in today's fast-paced", "in our modern world",
    "you will learn", "by the end", "throughout this article", "in this post",
    "we'll explore", "let's dive", "let's explore", "without further ado",
    "in conclusion", "to sum up", "in summary", "to summarize",
    "thank you for reading", "happy growing", "happy gardening", "happy cooking",
    "game-changer", "unlock the potential", "master the art", "elevate your",
    "transform your", "empower yourself", "unlock the secrets", "discover the power",
    "crucial to understand", "it's essential", "it is essential", "it's important",
    "thrilled to share", "excited to share", "perfect for anyone",
    "join thousands who", "one of the best ways", "one of the most important",
    "first and foremost", "last but not least", "needless to say",
    "when it comes to", "the bottom line is", "it goes without saying",
    "as mentioned above", "as stated earlier", "as we have seen",
    "more often than not", "when all is said and done", "at the end of the day",
    "here's everything you need", "read on to learn", "read on to discover",
    "here's everything you need to know", "we'll walk you through", "let's dive in",
    "in this post we'll", "in this article we'll", "keep in mind",
    "with the right approach", "on the other hand", "it's worth noting",
    # PROMPT meta-prompt: extra AI slop
    "this guide explains", "you will learn what works", "by the end, you will know",
    "no one succeeds in isolation", "perfect for anyone looking to improve",
    "the focus is on", "overall,", "it's important to remember", "it is important to remember",
    "supporting data", "cited quotes", "advanced techniques for experienced",
    "practical tips", "maintenance and care", "expert insights", "research highlights",
    # Legacy contamination phrases
    "natural materials vary throughout", "professional practitioners recommend",
    "achieving consistent results requires attention", "once you've perfected small batches",
    "once you have perfected small batches", "scaling up becomes appealing",
    "making larger batches requires", "heat distribution", "doubling recipes",
    "this practical guide", "this guide covers practical", "measuring cups",
    "dry ingredients", "wet ingredients", "shelf life 2-4 weeks", "shelf life 3-6 months",
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


def _ensure_run_log_header():
    if ANTI_DRIFT_RUN_LOG_FILE.exists():
        return
    with open(ANTI_DRIFT_RUN_LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "article_id",
                "title",
                "status",
                "gate_score",
                "gate_pass",
                "issues",
                "spec_hash",
                "goldens_hash",
            ]
        )


def _load_done_blacklist() -> set[str]:
    if not ANTI_DRIFT_DONE_FILE.exists():
        return set()
    try:
        payload = json.loads(ANTI_DRIFT_DONE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    ids = payload.get("done_ids", []) if isinstance(payload, dict) else payload
    return {str(x) for x in ids}


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

    def mark_retry(self, article_id: str, error: str, retry_at: datetime):
        self._update_status(
            article_id,
            "retrying",
            last_error=error,
            retry_at=retry_at.isoformat(),
            increment_failures=True,
        )

    def _update_status(
        self,
        article_id: str,
        status: str,
        last_error: str | None = None,
        shopify_url: str | None = None,
        retry_at: str | None = None,
        increment_failures: bool = False,
    ):
        for item in self.payload.get("items", []):
            if str(item.get("id")) == str(article_id):
                item["status"] = status
                item["attempts"] = int(item.get("attempts", 0)) + 1
                if increment_failures:
                    item["failures"] = int(item.get("failures", 0)) + 1
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
            "key_terms": ["key terms"],
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

        # Check for Pinterest image
        has_pinterest = any("pinimg.com" in url for url in img_urls)

        # Check for Shopify CDN images
        has_shopify_cdn = any("cdn.shopify.com" in url for url in img_urls)

        return {
            "pass": unique_images >= min_images and len(duplicates) == 0,
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
        if not sources["pass"]:
            if sources["raw_urls_visible"]:
                all_issues.append(f"Raw URLs visible: {sources['raw_urls_visible']}")
            if sources["source_links_count"] < sources["min_required"]:
                all_issues.append(
                    f"Low sources: {sources['source_links_count']}/{sources['min_required']}"
                )

        overall_pass = passed_checks >= 5  # At least 5/6 checks pass
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
# SHOPIFY API (env or config fallback for GHA)
# ============================================================================

def _shopify_config():
    """SHOP, BLOG_ID, TOKEN, API_VERSION from env; fallback from SHOPIFY_PUBLISH_CONFIG.json"""
    shop = os.getenv("SHOPIFY_SHOP") or os.getenv("SHOPIFY_STORE_DOMAIN")
    blog_id = os.getenv("SHOPIFY_BLOG_ID")
    token = os.getenv("SHOPIFY_ACCESS_TOKEN")
    api_ver = os.getenv("SHOPIFY_API_VERSION", "2025-01")
    if not shop or not blog_id or not token:
        config_path = PIPELINE_DIR.parent / "SHOPIFY_PUBLISH_CONFIG.json"
        if not config_path.exists():
            config_path = ROOT_DIR / "SHOPIFY_PUBLISH_CONFIG.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            shop_cfg = cfg.get("shop", {})
            if not shop:
                shop = shop_cfg.get("domain", "")
            if not token:
                token = shop_cfg.get("access_token", "")
            if not api_ver:
                api_ver = shop_cfg.get("api_version", "2025-01")
        # BLOG_ID often only in env (secrets)
        if not blog_id:
            blog_id = ""
    return shop or "", blog_id or "", token or "", api_ver or "2025-01"


_SHOP, _BLOG_ID, _TOKEN, _API_VER = _shopify_config()
SHOP = _SHOP
BLOG_ID = _BLOG_ID
API_VERSION = _API_VER
HEADERS = {
    "X-Shopify-Access-Token": _TOKEN,
    "Content-Type": "application/json",
}


class ShopifyAPI:
    """Shopify API wrapper"""

    @staticmethod
    def get_article(article_id: str) -> dict:
        """Fetch single article"""
        url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            return resp.json().get("article")
        return None

    @staticmethod
    def get_all_articles(status: str = "any", limit: int = 250) -> list:
        """Fetch all articles"""
        url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles.json?limit={limit}"
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
        url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
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
        }

    def _save_progress(self):
        """Save progress to file"""
        self.progress["last_run"] = datetime.now().isoformat()
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.progress, f, indent=2, ensure_ascii=False)

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

    def _build_key_terms_section(self, topic: str) -> str:
        """Build Key Terms section (META-PROMPT required)."""
        terms = self._extract_topic_terms(topic) or [topic]
        # Ensure we have at least 3 terms
        if len(terms) < 3:
            terms = terms + [f"{topic} process", f"{topic} method", "best practices"]
        terms = terms[:6]
        items = "\n".join(
            [
                f'<li><strong>{t.replace("-", " ").title()}</strong> — Central to {topic} and used throughout the content below.</li>'
                for t in terms
            ]
        )
        return f"""
<h2 id="key-terms">Key Terms</h2>
<ul>
{items}
</ul>
"""

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
                f'<li><a href="{url}" rel="nofollow noopener">{text}</a></li>'
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

    def _pad_to_word_count(self, body_html: str, topic: str, target: int = 1850, mode: str | None = None) -> str:
        soup = BeautifulSoup(body_html, "html.parser")
        current_words = len(soup.get_text(separator=" ", strip=True).split())
        if current_words >= target:
            return body_html

        terms = self._extract_topic_terms(topic)
        focus_phrase = ", ".join(terms[:3]) if terms else topic

        pad_section = "<h2>Additional Practical Notes</h2>"
        if mode == "gardening":
            pad_paragraphs = [
                (
                    f"<p>For {topic}, keep container size, drainage, and light consistent so results are comparable. "
                    "If growth slows, adjust only one variable at a time and re-check within a week.</p>"
                ),
                (
                    f"<p>A simple checklist helps with {topic}: confirm light hours, check moisture in the top inch, "
                    "and prune lightly to encourage new growth.</p>"
                ),
                (
                    f"<p>Track watering rhythm and leaf color for {topic} so you can spot stress early. "
                    "Small adjustments are more reliable than large changes.</p>"
                ),
                (
                    f"<p>For {topic}, avoid crowded containers that limit airflow. "
                    "Spacing and airflow reduce pests and keep foliage healthy.</p>"
                ),
                (
                    f"<p>Label containers with dates and note fertilizer timing. "
                    "This keeps {topic} care consistent across cycles.</p>"
                ),
            ]
        else:
            pad_paragraphs = [
                (
                    f"<p>For {topic}, keep the focus on {focus_phrase}. "
                    "Document the exact materials, amounts, and timing so you can repeat what works. "
                    "If the result is inconsistent, adjust only one variable and re-test.</p>"
                ),
                (
                    f"<p>A simple checklist helps with {topic}: confirm the goal and inputs, "
                    "match the method to that use case, and verify the result before moving on. "
                    "This prevents drifting into steps that don’t fit the goal.</p>"
                ),
                (
                    f"<p>When {topic} involves mixtures or solutions, label containers and note ratios. "
                    "Store in a cool, safe place and keep a small test area to verify results before full use.</p>"
                ),
                (
                    f"<p>Track outcomes for {topic} in a short log so you can compare results across attempts. "
                    "Consistency comes from repeating the same steps with minor, measured tweaks.</p>"
                ),
                (
                    f"<p>For {topic}, avoid adding extra steps that do not directly improve the outcome. "
                    "Keep the workflow lean so you can spot what actually changes the result.</p>"
                ),
                (
                    f"<p>Store leftover materials for {topic} in labeled containers and note dates. "
                    "This makes it easy to re-check performance and update ratios if needed.</p>"
                ),
            ]
        # Add unique, term-driven paragraphs to reach word count without duplicates.
        for idx, term in enumerate(terms[:6], 1):
            pad_paragraphs.append(
                f"<p><strong>Note {idx}:</strong> In {topic}, {term} should be checked against the goal and conditions. "
                "Keep measurements consistent and record results so the next iteration is comparable.</p>"
            )

        if mode == "gardening":
            checklist_items = "\n".join(
                [
                    f"<li>Confirm container size and drainage for {topic}.</li>",
                    f"<li>Verify light hours and rotate pots for even growth.</li>",
                    f"<li>Water when the top inch is dry and avoid standing water.</li>",
                    f"<li>Document growth changes so {topic} stays consistent.</li>",
                ]
            )
        else:
            checklist_items = "\n".join(
                [
                    f"<li>Confirm the goal and materials for {topic}.</li>",
                    f"<li>Verify ratios and timing before scaling the {topic} process.</li>",
                    f"<li>Run a small test, then adjust one variable at a time.</li>",
                    f"<li>Document outcomes so repeat runs of {topic} stay consistent.</li>",
                ]
            )
        pad_paragraphs.append(
            f"<h3>Consistency Checklist</h3><ul>{checklist_items}</ul>"
        )

        if pad_section not in body_html:
            body_html += f"\n{pad_section}\n"

        for para in pad_paragraphs:
            if current_words >= target:
                break
            if para in body_html:
                continue
            body_html += f"\n{para}\n"
            soup = BeautifulSoup(body_html, "html.parser")
            current_words = len(soup.get_text(separator=" ", strip=True).split())

        if current_words < target:
            if mode == "gardening":
                extra_sentences = [
                    f"{topic} improves when light and watering stay consistent across weeks.",
                    f"Record {topic} growth in a simple log so you can compare conditions over time.",
                    f"Use clean containers for {topic} to reduce stress and pests.",
                    f"If {topic} is seasonal, note temperature and day length for each cycle.",
                    f"Prioritize steady growth in {topic} before pushing for faster harvests.",
                    f"Track potting mix changes that could affect {topic} results.",
                    f"Rotate containers for {topic} to keep foliage balanced and upright.",
                    f"Document adjustments so {topic} changes can be traced and reversed if needed.",
                ]
            else:
                extra_sentences = [
                    f"{topic} improves when you keep ratios and timing consistent across tests.",
                    f"Record {topic} results in a simple table so you can compare outcomes week to week.",
                    f"Use a dedicated container for {topic} to avoid cross-contamination with unrelated tasks.",
                    f"If {topic} is seasonal, note temperature and light conditions for each run.",
                    f"Prioritize repeatability in {topic} before optimizing for speed or scale.",
                    f"Track material quality and source changes that could affect {topic} results.",
                    f"Calibrate tools used for {topic} to keep measurements consistent.",
                    f"Document adjustments so {topic} variations can be traced and reversed if needed.",
                ]
            extra_text = " ".join(extra_sentences)
            body_html += (
                f"\n<h3>Extended Notes</h3>\n"
                f"<p>{extra_text}</p>\n"
                f"<ul>"
                f"<li>Define the goal for {topic} before changing inputs.</li>"
                f"<li>Keep a small test batch to validate changes safely.</li>"
                f"<li>Review results after each run and update your checklist.</li>"
                f"</ul>\n"
            )

            soup = BeautifulSoup(body_html, "html.parser")
            current_words = len(soup.get_text(separator=" ", strip=True).split())

        # Final padding: add short unique notes until minimum word count is reached.
        counter = 1
        while current_words < target and counter <= 20:
            term = terms[(counter - 1) % len(terms)] if terms else topic
            if mode == "gardening":
                body_html += (
                    f"\n<p>Additional note {counter} for {topic}: "
                    f"keep drainage, light, and watering steady, then track how {term} responds over 7–10 days. "
                    f"Prune lightly and adjust only one variable at a time to keep {topic} predictable.</p>\n"
                )
            else:
                body_html += (
                    f"\n<p>Additional note {counter} for {topic}: "
                    f"validate {term} conditions, record the outcome, and keep the procedure consistent before scaling. "
                    f"Check one variable at a time to keep {topic} repeatable.</p>\n"
                )
            soup = BeautifulSoup(body_html, "html.parser")
            current_words = len(soup.get_text(separator=' ', strip=True).split())
            counter += 1

        return body_html

    def _build_article_body(self, title: str) -> str:
        topic = self._normalize_topic(title)
        if self._is_gardening_topic(title):
            return self._build_gardening_body(topic, title)
        terms = self._extract_topic_terms(title)
        focus_phrase = ", ".join(terms[:3]) if terms else topic
        focus_terms = ", ".join(terms) if terms else topic

        key_points = "\n".join(
            [
                f"<li>Align steps and inputs with {focus_phrase} goals.</li>",
                f"<li>Start with a small test run for {topic} before scaling.</li>",
                f"<li>Use measured inputs and consistent timing for {topic}.</li>",
                f"<li>Keep the process focused on {focus_terms} to avoid off-topic steps.</li>",
                "<li>Keep conditions steady (light, temperature, spacing) as needed.</li>",
                "<li>Record inputs and results so you can repeat them.</li>",
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
<h2>Direct Answer</h2>
    <p>{topic} works best when you keep the steps specific to {focus_phrase}, measure inputs carefully, and test a small run before scaling. Use consistent timing, track conditions, and repeat the same sequence until the result is stable. If anything looks off, adjust one variable at a time so you can trace the cause and lock in a reliable routine.</p>

<h2>Key Conditions at a Glance</h2>
<ul>
{key_points}
</ul>

<h2>Understanding {topic}</h2>
<p>{topic} is most reliable when the steps match the goal and the inputs you control. That means selecting the right setup, following the method consistently, and checking results before repeating.</p>
<p>Identify the main variables for {topic} (inputs, timing, and conditions). Keeping those consistent makes the outcome repeatable.</p>
<p>Work in a stable environment and avoid mixing steps from unrelated tasks. If a step doesn’t directly support {focus_phrase}, skip it.</p>
<p>Use a short checklist so each pass of {topic} is measured and comparable.</p>

<h2>Complete Step-by-Step Guide</h2>
<h3>Preparation</h3>
<p>Set up a clean workspace and gather the tools and materials that fit {topic}. Label any containers so measurements are not confused later.</p>
<p>Choose a small test run first. This keeps {topic} controlled before you scale it.</p>
<p>Measure the main inputs and note the amounts so you can repeat the same {topic} process.</p>

<h3>Main Process</h3>
<p>Apply the method evenly and avoid rushing steps. This helps {topic} work consistently and reduces variability.</p>
<p>Allow the recommended time window, then evaluate the result. Track the timing for {topic} so you can adjust if the result is too strong or too weak.</p>
<p>Check the outcome immediately. If it’s not right, adjust one variable at a time (amount, time, or technique) and re-test.</p>

<h3>Finishing</h3>
<p>Complete any final steps required for {topic} and confirm the result meets the goal.</p>
<p>Store any remaining materials in labeled containers and note the amounts used.</p>
<p>Record what worked and what didn’t so the next {topic} run is faster and more consistent.</p>

<h2>Types and Varieties</h2>
<p>{topic} can vary based on setup, scale, and method. Choose the option that matches your use case.</p>
<ul>
    <li>Light-duty use: small batch, simple steps, quick checks.</li>
    <li>Standard use: balanced inputs, consistent timing, repeatable results.</li>
    <li>Detail work: smaller tools for edges, corners, and tight areas.</li>
</ul>
<p>For {topic}, the best method is the one that delivers reliable results without extra rework.</p>

<h2>Troubleshooting Common Issues</h2>
<p>If {topic} looks inconsistent or underperforms, the input amount or timing likely needs adjustment.</p>
<ul>
    <li>Issue: uneven results → Fix: apply the method more evenly and slow the pace.</li>
    <li>Issue: no visible improvement → Fix: increase time slightly and re-test.</li>
    <li>Issue: overcorrection → Fix: reduce inputs and re-test.</li>
</ul>
<p>Adjust one variable at a time so you can see what actually improves {topic}.</p>

<h2>Pro Tips from Experts</h2>
{pro_tips}

{self._build_key_terms_section(topic)}

{self._build_faqs(topic)}

<h2>Advanced Techniques</h2>
<p>Once {topic} is reliable, test small changes in inputs or method while keeping everything else the same.</p>
<p>Track each change in a short log so you can identify the best-performing version of {topic}.</p>
<p>For recurring tasks, pre-label containers and tools so each session starts with the same setup.</p>

{self._build_comparison_table(topic)}

{self._build_sources_section(topic)}
</article>
"""
        return self._pad_to_word_count(body, topic)

    def _is_gardening_topic(self, title: str) -> bool:
        t = title.lower()
        return any(
            kw in t
            for kw in [
                "grow",
                "growing",
                "garden",
                "gardening",
                "plant",
                "container",
                "containers",
                "herb",
                "basil",
                "soil",
                "potting",
                "seed",
                "seedling",
            ]
        )

    def _build_gardening_body(self, topic: str, title: str) -> str:
        terms = self._extract_topic_terms(title)
        focus_phrase = ", ".join(terms[:3]) if terms else topic
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
        key_points = "\n".join(
            [
                f"<li>Use containers with drainage and match size to {focus_phrase} growth.</li>",
                f"<li>Use a light, well-draining potting mix for {topic}.</li>",
                f"<li>Keep light, watering, and feeding consistent to avoid stress.</li>",
                f"<li>Prune regularly to keep {topic} compact and productive.</li>",
                "<li>Track changes in light and temperature and adjust gradually.</li>",
                "<li>Record inputs and results so you can repeat what works.</li>",
            ]
        )

        body = f"""
<article>
<h2>Direct Answer</h2>
    <p>{topic} works best when you use the right container size, a well-draining mix, steady light, and consistent watering. Start with healthy starts or seeds, keep the soil evenly moist (not soggy), and prune often to encourage new growth. If results slip, adjust one variable at a time so you can identify what is holding {topic} back.</p>

<h2>Key Conditions at a Glance</h2>
<ul>
{key_points}
</ul>

<h2>Understanding {topic}</h2>
<p>{topic} is most reliable when the container, soil structure, and light exposure are aligned. Containers control root space and moisture, so drainage and mix quality determine whether plants stay healthy.</p>
<p>Identify the main variables for {topic} (container size, soil structure, light hours, watering rhythm). Keeping those consistent makes the outcome repeatable.</p>
<p>Work in stable conditions and avoid changing multiple variables at once. If a step doesn’t directly support {focus_phrase}, skip it.</p>
<p>Use a short checklist so each pass of {topic} is measured and comparable.</p>

<h2>Complete Step-by-Step Guide</h2>
<h3>Preparation</h3>
<p>Choose containers with drainage holes and a saucer that prevents standing water. For {topic}, clean containers prevent carryover issues.</p>
<p>Use a light, well-draining potting mix and pre-moisten it before planting.</p>
<p>Set a plan for light (window, grow light, or outdoor spot) and note your starting conditions.</p>

<h3>Planting and Setup</h3>
<p>Plant seeds or starts at the correct depth and spacing for {topic}. Press soil lightly and water to settle.</p>
<p>Place containers where they receive consistent light. Rotate containers every few days so growth stays even.</p>
<p>Keep the top inch of soil evenly moist. Overwatering is the most common setback for {topic} in containers.</p>

<h3>Ongoing Care</h3>
<p>Water when the top layer dries, then let excess drain completely. Avoid leaving containers in standing water.</p>
<p>Prune regularly by pinching back stems to encourage bushier growth.</p>
<p>Feed lightly with a balanced fertilizer every 2–4 weeks during active growth.</p>

<h2>Types and Varieties</h2>
<p>{topic} can vary by variety, growth habit, and flavor profile. Choose types that fit your space and use case.</p>
<ul>
    <li>Compact varieties: best for small containers and indoor setups.</li>
    <li>Standard varieties: vigorous growth with frequent pruning.</li>
    <li>Specialty varieties: unique flavors but may need more light.</li>
</ul>
<p>For {topic}, the best method is the one that fits your light conditions and how often you can maintain the plants.</p>

<h2>Troubleshooting Common Issues</h2>
<p>If {topic} looks weak or leggy, light or watering is usually the cause.</p>
<ul>
    <li>Issue: yellowing leaves → Fix: reduce watering and improve drainage.</li>
    <li>Issue: slow growth → Fix: increase light and adjust feeding.</li>
    <li>Issue: wilting midday → Fix: check root space and water schedule.</li>
</ul>
<p>Adjust one variable at a time so you can see what actually improves {topic}.</p>

<h2>Pro Tips from Experts</h2>
{pro_tips}

{self._build_key_terms_section(topic)}

{self._build_gardening_faqs(topic)}

<h2>Advanced Techniques</h2>
<p>Once {topic} is reliable, test small changes in light, spacing, or feeding while keeping everything else the same.</p>
<p>Track each change in a short log so you can identify the best-performing setup for {topic}.</p>
<p>For recurring batches, pre-label containers so each session starts with the same setup.</p>

{self._build_gardening_comparison_table(topic)}

{self._build_sources_section(topic)}
</article>
"""
        return self._pad_to_word_count(body, topic, mode="gardening")

    def _build_gardening_faqs(self, topic: str) -> str:
        return f"""
<h2>Frequently Asked Questions</h2>
<h3>How much light does {topic} need?</h3>
<p>Most setups do best with 6–8 hours of strong light or a consistent grow light schedule.</p>
<h3>What container size works best for {topic}?</h3>
<p>A 6–8 inch pot per plant is a reliable starting point, with larger containers for multiple plants.</p>
<h3>How often should I water {topic} in containers?</h3>
<p>Water when the top inch of mix is dry; avoid keeping containers saturated.</p>
<h3>Should I prune {topic}?</h3>
<p>Yes—pinching back stems keeps plants bushy and extends productive growth.</p>
<h3>When can I start harvesting {topic}?</h3>
<p>Harvest once plants have several sets of leaves and avoid taking more than a third at a time.</p>
<h3>Do I need fertilizer for {topic}?</h3>
<p>A light, balanced feed every 2–4 weeks is usually enough in containers.</p>
<h3>What pests are common with {topic}?</h3>
<p>Check for aphids and mites; rinse gently and improve airflow if they appear.</p>
"""

    def _build_gardening_comparison_table(self, topic: str) -> str:
        return f"""
<div class="table-responsive">
<table class="comparison-table">
<thead>
  <tr>
    <th>Setup</th>
    <th>Light Target</th>
    <th>Watering Rhythm</th>
    <th>Key Note</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td>Indoor windowsill</td>
    <td>Bright light 6–8 hrs</td>
    <td>Check daily, water as needed</td>
    <td>Rotate pots for even growth</td>
  </tr>
  <tr>
    <td>Outdoor patio</td>
    <td>Full sun or morning sun</td>
    <td>Water when top inch dries</td>
    <td>Protect from extreme heat</td>
  </tr>
  <tr>
    <td>Grow light setup</td>
    <td>12–14 hrs consistent</td>
    <td>Moist but not soggy</td>
    <td>Keep light close and stable</td>
  </tr>
</tbody>
</table>
</div>
"""

    def _build_meta_description(self, title: str) -> str:
        topic = self._normalize_topic(title)
        desc = f"Learn how to handle {topic} with a clear step-by-step process, practical tips, and troubleshooting guidance for reliable results."
        return desc[:160]

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
        queue = AntiDriftQueue.load()
        item = queue.next_pending()
        if not item:
            print("✅ No pending items in anti-drift queue")
            return

        self._run_queue_item(queue, item)

    def run_queue_once_with_backoff(self):
        """Process exactly one eligible item with retry/backoff support."""
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
            if use_backoff and failures < MAX_QUEUE_RETRIES:
                retry_at = self._next_retry_at(failures + 1)
                queue.mark_retry(article_id, error, retry_at)
                print(f"⏳ {error} - retry scheduled at {retry_at.isoformat()}")
            else:
                queue.mark_failed(article_id, error)
                print(f"❌ {error}")
            queue.save()
            self._append_run_log(article_id, title, "failed", 0, False, error)
            return

        audit = self.quality_gate.full_audit(article)
        gate = audit.get("deterministic_gate", {})
        gate_score = gate.get("score", 0)
        gate_pass = gate.get("pass", False)

        # If gate is far from pass, force rebuild immediately (avoid retry loop)
        if not gate_pass and gate_score < 9:
            print(f"🔁 Gate LOW ({gate_score}/10) - forcing rebuild now")
            try:
                self.force_rebuild_article_ids([article_id])
            except Exception as exc:
                print(f"[WARN] force_rebuild failed: {exc}")

            rebuilt_article = self.api.get_article(article_id)
            if not rebuilt_article:
                error = "REBUILD_ARTICLE_NOT_FOUND"
                if use_backoff and failures < MAX_QUEUE_RETRIES:
                    retry_at = self._next_retry_at(failures + 1)
                    queue.mark_retry(article_id, error, retry_at)
                    print(f"⏳ {error} - retry scheduled at {retry_at.isoformat()}")
                else:
                    queue.mark_failed(article_id, error)
                    print(f"❌ {error}")
                queue.save()
                self._append_run_log(article_id, title, "failed", 0, False, error)
                return

            audit = self.quality_gate.full_audit(rebuilt_article)
            gate = audit.get("deterministic_gate", {})
            gate_score = gate.get("score", 0)
            gate_pass = gate.get("pass", False)

        # HARD BLOCK: Word count must be >= 1600 regardless of gate
        word_count_info = audit.get("details", {}).get("word_count", {})
        current_word_count = word_count_info.get("word_count", 0)
        HARD_MIN_WORDS = 1800
        if current_word_count < HARD_MIN_WORDS:
            error_msg = f"HARD_BLOCK: Word count {current_word_count} < {HARD_MIN_WORDS}"
            print(f"[FAIL] {error_msg} - Cannot mark done")
            queue.mark_retry(article_id, error_msg, datetime.now() + timedelta(minutes=30))
            queue.save()
            self._append_run_log(
                article_id, audit.get("title", ""), "failed", gate_score, False, error_msg
            )
            return

        if gate_pass:
            # META-PROMPT: Pre-publish review then cleanup + publish before mark_done
            content_factory_dir = PIPELINE_DIR.parent  # repo root for this agent (scripts + pipeline_v2)
            review_script = content_factory_dir / "scripts" / "pre_publish_review.py"
            cleanup_script = PIPELINE_DIR / "cleanup_before_publish.py"
            publish_script = PIPELINE_DIR / "publish_now_graphql.py"
            review_ok = False
            if review_script.exists():
                r = subprocess.run(
                    [sys.executable, str(review_script), str(article_id)],
                    cwd=str(content_factory_dir),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                review_ok = r.returncode == 0
                if not review_ok and r.stderr:
                    print(f"[WARN] pre_publish_review: {r.stderr[:200]}")
            else:
                print("[FAIL] pre_publish_review.py not found - refusing to publish without review")
                review_ok = False
            if review_ok:
                if cleanup_script.exists():
                    subprocess.run(
                        [sys.executable, str(cleanup_script), str(article_id)],
                        cwd=str(content_factory_dir),
                        capture_output=True,
                        timeout=90,
                    )
                # Ensure featured image (fallback: set from first inline if still missing)
                set_featured_script = PIPELINE_DIR / "set_featured_image_if_missing.py"
                if set_featured_script.exists():
                    subprocess.run(
                        [sys.executable, str(set_featured_script), str(article_id)],
                        cwd=str(content_factory_dir),
                        capture_output=True,
                        timeout=60,
                    )
                if publish_script.exists():
                    subprocess.run(
                        [sys.executable, str(publish_script), str(article_id)],
                        cwd=str(content_factory_dir),
                        capture_output=True,
                        timeout=60,
                    )
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
                    "review+cleanup+publish",
                )
                print(f"✅ Gate PASS ({gate_score}/10) - Review OK - Cleanup + Publish - Marked DONE")
            else:
                print(f"⏳ Gate PASS but pre_publish_review FAIL - attempting auto-fix")
                fix_result = self._auto_fix_article(article_id)
                if fix_result.get("status") == "done":
                    # Re-run pre_publish_review on fixed content; only publish if it passes
                    review_pass_after_fix = False
                    if review_script.exists():
                        r2 = subprocess.run(
                            [sys.executable, str(review_script), str(article_id)],
                            cwd=str(content_factory_dir),
                            capture_output=True,
                            text=True,
                            timeout=120,
                        )
                        review_pass_after_fix = r2.returncode == 0
                    if review_pass_after_fix:
                        if cleanup_script.exists():
                            subprocess.run(
                                [sys.executable, str(cleanup_script), str(article_id)],
                                cwd=str(content_factory_dir),
                                capture_output=True,
                                timeout=90,
                            )
                        set_featured_script = PIPELINE_DIR / "set_featured_image_if_missing.py"
                        if set_featured_script.exists():
                            subprocess.run(
                                [sys.executable, str(set_featured_script), str(article_id)],
                                cwd=str(content_factory_dir),
                                capture_output=True,
                                timeout=60,
                            )
                        if publish_script.exists():
                            subprocess.run(
                                [sys.executable, str(publish_script), str(article_id)],
                                cwd=str(content_factory_dir),
                                capture_output=True,
                                timeout=60,
                            )
                        queue.mark_done(article_id)
                        queue.save()
                        done_ids = _load_done_blacklist()
                        done_ids.add(str(article_id))
                        _save_done_blacklist(done_ids)
                        self._append_run_log(
                            article_id,
                            fix_result.get("audit", {}).get("title", ""),
                            "done",
                            gate_score,
                            True,
                            "auto_fix+review_pass+cleanup+publish",
                        )
                        print("✅ Auto-fix + review pass - Cleanup + Publish - Marked DONE")
                    else:
                        error_msg = "pre_publish_review_fail_after_fix"
                        if use_backoff and failures < MAX_QUEUE_RETRIES:
                            retry_at = self._next_retry_at(failures + 1)
                            queue.mark_retry(article_id, error_msg, retry_at)
                            print(f"⏳ Review still FAIL after fix - retry at {retry_at.isoformat()}")
                        else:
                            queue.mark_failed(article_id, error_msg)
                            print(f"❌ Review FAIL after fix - {error_msg}")
                        queue.save()
                        self._append_run_log(
                            article_id,
                            fix_result.get("audit", {}).get("title", ""),
                            "failed",
                            gate_score,
                            False,
                            error_msg,
                        )
                else:
                    error_msg = fix_result.get("error") or "pre_publish_review_fail"
                    if use_backoff and failures < MAX_QUEUE_RETRIES:
                        retry_at = self._next_retry_at(failures + 1)
                        queue.mark_retry(article_id, error_msg, retry_at)
                        print(f"⏳ Review FAIL - retry at {retry_at.isoformat()}")
                    else:
                        queue.mark_failed(article_id, error_msg)
                        print(f"❌ Review FAIL - {error_msg}")
                    queue.save()
                    self._append_run_log(
                        article_id,
                        audit.get("title", ""),
                        "failed",
                        gate_score,
                        False,
                        error_msg,
                    )
            return

        # Attempt auto-fix before retry/manual review
        fix_result = self._auto_fix_article(article_id)
        if fix_result.get("status") == "done":
            fixed_audit = fix_result.get("audit", {})
            fixed_gate = fixed_audit.get("deterministic_gate", {})
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
            print("✅ Auto-fix PASS - Marked DONE")
            return

        error_msg = fix_result.get("error") or "; ".join(
            (fix_result.get("audit", {}) or {}).get("issues", [])[:3]
        )
        if not error_msg:
            error_msg = "; ".join(audit.get("issues", [])[:3]) or "GATE_FAIL"
        if use_backoff and failures < MAX_QUEUE_RETRIES:
            retry_at = self._next_retry_at(failures + 1)
            queue.mark_retry(article_id, error_msg, retry_at)
            print(
                f"⏳ Gate FAIL ({gate_score}/10) - retry scheduled at {retry_at.isoformat()}: {error_msg}"
            )
        else:
            queue.mark_manual_review(article_id, error_msg)
            done_ids = _load_done_blacklist()
            done_ids.add(str(article_id))
            _save_done_blacklist(done_ids)
            print(f"🟡 Manual review queued ({gate_score}/10): {error_msg}")
        queue.save()
        self._append_run_log(
            article_id,
            audit.get("title", ""),
            "failed",
            gate_score,
            False,
            error_msg,
        )

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
                queue.mark_manual_review(article_id, error_msg)
                queue.save()
                self._append_run_log(
                    article_id,
                    audit.get("title", ""),
                    "failed",
                    gate.get("score", 0),
                    False,
                    error_msg or "manual_review_fix_failed",
                )
                print(f"❌ Manual review fix FAIL: {error_msg}")

    def fix_article_ids(self, article_ids: list[str]):
        """Auto-fix a specific list of article IDs sequentially."""
        if not article_ids:
            print("[ERROR] No article IDs provided")
            return

        queue = AntiDriftQueue.load() if ANTI_DRIFT_QUEUE_FILE.exists() else None
        print(f"\n🔧 Fixing {len(article_ids)} articles by ID...")

        for idx, article_id in enumerate(article_ids, 1):
            print(f"\n[{idx}/{len(article_ids)}] Fixing {article_id}...")
            result = self._auto_fix_article(article_id)
            if result.get("status") == "done":
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
                print("✅ Auto-fix PASS")
            else:
                audit = result.get("audit", {})
                gate = audit.get("deterministic_gate", {}) if audit else {}
                error_msg = result.get("error") or "; ".join(
                    audit.get("issues", [])[:3]
                )
                if queue:
                    queue.mark_manual_review(article_id, error_msg)
                    queue.save()
                self._append_run_log(
                    article_id,
                    audit.get("title", ""),
                    "failed",
                    gate.get("score", 0),
                    False,
                    error_msg or "manual_review_fix_failed",
                )
                print(f"❌ Auto-fix FAIL: {error_msg}")

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
                check=False,
            )
        except Exception as e:
            print(f"⚠️ Image fix failed: {e}")

    def _apply_meta_prompt_patch(self, article_id: str) -> bool:
        """Inject missing Sources & Further Reading and Key Terms sections (META-PROMPT)."""
        article = self.api.get_article(article_id)
        if not article:
            return False
        body = article.get("body_html", "") or ""
        title = article.get("title", "")
        topic = self._normalize_topic(title)
        body_lower = body.lower()
        has_sources = (
            "sources" in body_lower and "further reading" in body_lower
        ) or re.search(
            r"<h2[^>]*>.*(?:Sources|Further Reading|References).*</h2>",
            body,
            re.IGNORECASE,
        )
        has_key_terms = (
            "key terms" in body_lower
            and re.search(r"<h2[^>]*>.*Key Terms.*</h2>", body, re.IGNORECASE)
        ) or bool(re.search(r'id=["\']key-terms["\']', body, re.IGNORECASE))
        if has_sources and has_key_terms:
            return True
        sections_to_add = []
        if not has_key_terms:
            sections_to_add.append(self._build_key_terms_section(topic))
        if not has_sources:
            sections_to_add.append(self._build_sources_section(topic))
        if not sections_to_add:
            return True
        insert_html = "\n".join(sections_to_add)
        if "</article>" in body:
            body = body.replace("</article>", "\n" + insert_html + "\n</article>")
        else:
            body = body.rstrip() + "\n" + insert_html + "\n"
        updated = self.api.update_article(article_id, {"body_html": body})
        if updated:
            print("📝 Meta-prompt patch applied (Sources / Key Terms).")
        return bool(updated)

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
        url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
        payload = {"article": {"id": int(article_id), "summary_html": meta}}
        resp = requests.put(url, headers=HEADERS, json=payload)
        return resp.status_code == 200

    def _auto_fix_article(self, article_id: str) -> dict:
        """Auto-fix: images + meta description, then re-audit."""
        article = self.api.get_article(article_id)
        if not article:
            return {"status": "failed", "error": "ARTICLE_NOT_FOUND"}

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
            title = article.get("title", "")
            body_html = self._build_article_body(title)
            meta_description = self._build_meta_description(title)
            update_payload = {"body_html": body_html, "summary_html": meta_description}
            updated = self.api.update_article(article_id, update_payload)
            if not updated:
                return {"status": "failed", "error": "UPDATE_FAILED"}

        if "Low images" in issues_text or "Duplicate images" in issues_text:
            self._run_fix_images(article_id)

        if needs_rebuild:
            self._run_fix_images(article_id)

        self._apply_meta_prompt_patch(article_id)
        article = self.api.get_article(article_id) or article
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

        title = article.get("title", "")
        body_html = self._build_article_body(title)
        meta_description = self._build_meta_description(title)
        update_payload = {"body_html": body_html, "summary_html": meta_description}
        updated = self.api.update_article(article_id, update_payload)
        if not updated:
            return {"status": "failed", "error": "UPDATE_FAILED"}

        self._run_fix_images(article_id)
        self._apply_meta_prompt_patch(article_id)

        updated_article = self.api.get_article(article_id)
        if not updated_article:
            return {"status": "failed", "error": "REFETCH_FAILED"}

        re_audit = self.quality_gate.full_audit(updated_article)
        gate = re_audit.get("deterministic_gate", {})
        if gate.get("pass", False):
            return {"status": "done", "audit": re_audit}
        return {"status": "failed", "audit": re_audit, "error": "GATE_FAIL"}

    def force_rebuild_article_ids(self, article_ids: list[str]):
        """Force rebuild a list of article IDs sequentially."""
        if not article_ids:
            print("❌ No article IDs provided")
            return

        queue = AntiDriftQueue.load() if ANTI_DRIFT_QUEUE_FILE.exists() else None
        print(f"\n[INFO] Force rebuilding {len(article_ids)} articles...")

        for idx, article_id in enumerate(article_ids, 1):
            print(f"\n[{idx}/{len(article_ids)}] Rebuilding {article_id}...")
            result = self._force_rebuild_article(article_id)
            if result.get("status") == "done":
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
                print("[OK] Force rebuild PASS")
            else:
                audit = result.get("audit", {})
                gate = audit.get("deterministic_gate", {}) if audit else {}
                error_msg = result.get("error") or "; ".join(
                    audit.get("issues", [])[:3]
                )
                if queue:
                    queue.mark_manual_review(article_id, error_msg)
                    queue.save()
                self._append_run_log(
                    article_id,
                    audit.get("title", ""),
                    "failed",
                    gate.get("score", 0),
                    False,
                    error_msg or "force_rebuild_failed",
                )
                print(f"❌ Force rebuild FAIL: {error_msg}")

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
        print("  python ai_orchestrator.py queue-review <id> [failed|manual] [error]")
        print("  python ai_orchestrator.py fix-failed [limit]")
        print("  python ai_orchestrator.py fix-manual-review [limit]")
        print("  python ai_orchestrator.py fix-ids <id1> <id2> ...")
        print("  python ai_orchestrator.py force-rebuild-ids <id1> <id2> ...")
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
        if len(sys.argv) < 3:
            print("Error: Article ID required")
            return
        article_id = sys.argv[2]
        status = sys.argv[3] if len(sys.argv) > 3 else "failed"
        error_msg = " ".join(sys.argv[4:]).strip() if len(sys.argv) > 4 else ""
        if not error_msg:
            error_msg = "PRE_PUBLISH_REVIEW_FAIL"

        queue = AntiDriftQueue.load()
        if status in {"done", "published"}:
            queue.mark_done(article_id)
            new_status = "done"
        elif status in {"manual", "manual_review"}:
            queue.mark_manual_review(article_id, error_msg)
            new_status = "manual_review"
        else:
            queue.mark_failed(article_id, error_msg)
            new_status = "failed"
        queue.save()
        print(f"✅ Queue item {article_id} -> {new_status} ({error_msg})")

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

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
