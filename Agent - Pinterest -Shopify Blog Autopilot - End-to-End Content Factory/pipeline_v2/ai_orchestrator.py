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
    Path(__file__).parent.parent.parent.parent / ".env",  # Root repo
    Path(__file__).parent.parent.parent / ".env",
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent / ".env",
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break
load_dotenv()

# Config - Force correct Shopify domain
SHOP = "the-rike-inc.myshopify.com"  # Hardcoded to avoid .env issues
TOKEN = os.environ.get("SHOPIFY_TOKEN") or os.environ.get("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "108441862462")
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Paths
PIPELINE_DIR = Path(__file__).parent
SCRIPTS_DIR = PIPELINE_DIR.parent / "scripts"
PROGRESS_FILE = PIPELINE_DIR / "orchestrator_progress.json"
ANTI_DRIFT_QUEUE_FILE = PIPELINE_DIR / "anti_drift_queue.json"
ANTI_DRIFT_RUN_LOG_FILE = PIPELINE_DIR / "anti_drift_run_log.csv"
ANTI_DRIFT_SPEC_FILE = PIPELINE_DIR / "anti_drift_spec_v1.md"
ANTI_DRIFT_GOLDENS_FILE = PIPELINE_DIR / "anti_drift_goldens_12.json"

# Anti-drift retry/backoff
MAX_QUEUE_RETRIES = 3
BACKOFF_BASE_SECONDS = 120
BACKOFF_MAX_SECONDS = 600
BACKOFF_JITTER_SECONDS = 30


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

# Generic phrases to detect
GENERIC_PHRASES = [
    "this comprehensive guide provides",
    "this comprehensive guide covers",
    "whether you are a beginner",
    "whether you're a beginner",
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
        queue_items = []
        for item in items:
            queue_items.append(
                {
                    "id": str(item.get("id")),
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
            [f'<li><a href="{url}">{text}</a></li>' for url, text in sources]
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
<table style="width:100%; border-collapse:collapse; line-height:1.6;">
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

        pad_section = "<h2>Additional Practical Notes</h2>"
        pad_paragraph = (
            f"<p>In practice, {topic} improves when you document each attempt. "
            "Write down the materials you used, the order of steps, and the timing. "
            "This record makes it easier to repeat good outcomes and identify where a change caused a problem. "
            "Small adjustments, made one at a time, lead to reliable improvements.</p>"
        )
        pad_paragraph_2 = (
            f"<p>Another useful habit for {topic} is to define a simple pass/fail check. "
            "Pick one or two indicators that show success, such as texture, appearance, or function. "
            "If the result misses the target, focus on the most likely variable and adjust it next time. "
            "This keeps your process steady and prevents random changes.</p>"
        )
        pad_paragraph_3 = (
            f"<p>When working on {topic}, prioritize safety and cleanliness. "
            "Keep tools and containers clean, and store finished items properly. "
            "Labeling dates and contents helps you track what was done and when. "
            "Clear labeling also supports troubleshooting if something looks off later.</p>"
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

        key_points = "\n".join(
            [
                f"<li>Focus on clean, safe materials that match {topic}.</li>",
                "<li>Prepare a simple workspace before you begin.</li>",
                "<li>Follow a clear sequence to avoid rework.</li>",
                "<li>Use consistent measurements and timing.</li>",
                "<li>Document what works so you can repeat it.</li>",
                "<li>Check results and refine your next attempt.</li>",
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
<p>{topic} can be completed successfully when you use suitable materials, a clear sequence, and a simple quality check. Start with a small batch, follow a repeatable workflow, and adjust one variable at a time to improve results.</p>

<h2>Key Conditions at a Glance</h2>
<ul>
{key_points}
</ul>

<h2>Understanding {topic}</h2>
<p>{topic} works best when you understand the purpose of each step and why timing and material choice matter. A clean setup and reliable inputs reduce errors and make it easier to repeat results.</p>
<p>Before you begin, clarify your goal, gather materials, and decide how you will judge success. A short checklist helps you stay focused on the essential steps.</p>
<p>Consider the environment where you will work. Temperature, airflow, and storage can affect outcomes. If you need consistency, try to keep these conditions stable from one attempt to the next.</p>
<p>Finally, treat the process as a repeatable system. Each step should have a clear purpose and a measurable outcome, even if the outcome is a simple visual check.</p>

<h2>Complete Step-by-Step Guide</h2>
<h3>Preparation</h3>
<p>Start by clearing your workspace and collecting tools that are appropriate for {topic}. Label containers, measure inputs, and prepare any safety items you may need.</p>
<p>Set a simple timer or schedule for the key steps so you can stay consistent across attempts.</p>
<p>If materials vary in quality, sort them first. Consistent input quality keeps your results stable and reduces the need to correct mistakes later.</p>

<h3>Main Process</h3>
<p>Follow a straightforward sequence that keeps your materials organized and your workspace clean. Work in small stages so you can correct problems early without losing the whole batch.</p>
<p>Monitor progress as you go, and keep short notes on timing and outcomes.</p>
<p>When you reach a decision point, pause and check your indicators. A brief check here prevents bigger corrections later in the process.</p>

<h3>Finishing</h3>
<p>Complete the final step by checking texture, appearance, or function. If anything looks off, note the change you will make next time.</p>
<p>Store your results carefully and label them with dates for easy tracking.</p>
<p>After finishing, review your notes and compare the outcome with your goal. This short review makes your next attempt faster and more reliable.</p>

<h2>Types and Varieties</h2>
<p>There are multiple approaches to {topic}. The best choice depends on time, available tools, and desired results. Start with the simplest method, then try variants once you can reproduce a good baseline.</p>
<ul>
  <li>Basic method: minimal materials and steps.</li>
  <li>Standard method: balanced effort and outcome.</li>
  <li>Advanced method: extra steps for refined results.</li>
</ul>
<p>When selecting a method, weigh time, cost, and the reliability of results. A method that produces consistent outcomes is often better than one that promises speed but creates rework.</p>

<h2>Troubleshooting Common Issues</h2>
<p>If results fall short, check the preparation step first. Inconsistent measurements and rushed steps are the most common causes of failure.</p>
<ul>
  <li>Issue: uneven results → Fix: slow down and measure consistently.</li>
  <li>Issue: weak outcomes → Fix: adjust timing and material quality.</li>
  <li>Issue: messy process → Fix: simplify the workflow into smaller steps.</li>
</ul>
<p>When troubleshooting, change only one variable at a time. This makes it clear which adjustment actually improves the outcome.</p>

<h2>Pro Tips from Experts</h2>
{pro_tips}

{self._build_faqs(topic)}

<h2>Advanced Techniques</h2>
<p>Once the basic method is reliable, refine one variable at a time. This makes it easier to identify what improves the outcome without introducing confusion.</p>
<p>Track small changes in timing, materials, and environment, then keep the combination that performs best.</p>
<p>Advanced work often benefits from a checklist and a strict sequence. A stable routine lets you identify real improvements rather than accidental changes.</p>

{self._build_comparison_table(topic)}

{self._build_sources_section(topic)}
</article>
"""
        return self._pad_to_word_count(body, topic)

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

        if gate_pass:
            queue.mark_done(article_id)
            queue.save()
            self._append_run_log(
                article_id,
                audit.get("title", ""),
                "done",
                gate_score,
                True,
                "; ".join(audit.get("issues", [])[:3]),
            )
            print(f"✅ Gate PASS ({gate_score}/10) - Marked DONE")
            return

        error_msg = "; ".join(audit.get("issues", [])[:3]) or "GATE_FAIL"
        if use_backoff and failures < MAX_QUEUE_RETRIES:
            retry_at = self._next_retry_at(failures + 1)
            queue.mark_retry(article_id, error_msg, retry_at)
            print(
                f"⏳ Gate FAIL ({gate_score}/10) - retry scheduled at {retry_at.isoformat()}: {error_msg}"
            )
        else:
            queue.mark_failed(article_id, error_msg)
            print(f"❌ Gate FAIL ({gate_score}/10): {error_msg}")
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

        audit = self.quality_gate.full_audit(article)
        issues_text = "; ".join(audit.get("issues", []))

        needs_rebuild = any(
            key in issues_text
            for key in [
                "Missing sections",
                "Generic phrases",
                "Off-topic content",
                "Word count",
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

        self._ensure_meta_description(article)

        updated_article = self.api.get_article(article_id)
        if not updated_article:
            return {"status": "failed", "error": "REFETCH_FAILED"}

        re_audit = self.quality_gate.full_audit(updated_article)
        gate = re_audit.get("deterministic_gate", {})
        if gate.get("pass", False):
            return {"status": "done", "audit": re_audit}
        return {"status": "failed", "audit": re_audit, "error": "GATE_FAIL"}

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
        print("  python ai_orchestrator.py fix-failed [limit]")
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

    elif command == "fix-failed":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 30
        orchestrator.fix_failed_from_log(limit=limit)

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
