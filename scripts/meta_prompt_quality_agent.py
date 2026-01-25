#!/usr/bin/env python3
"""
🤖 META-PROMPT QUALITY AGENT
Kiểm tra chất lượng nội dung blog theo ĐÚNG tiêu chuẩn META-PROMPT

TIÊU CHUẨN TỪ META-PROMPT:
- WORD_BUDGET: 1800-2200 words
- Citations: ≥5 primary sources (.gov/.edu/journal)
- Expert Quotes: ≥2 với tên + chức danh
- Statistics: ≥3 quantified stats
- H2/H3: unique kebab-case ids
- Direct Answer: 50-70 words ở đầu bài
- FAQ: 5-7 questions (if INCLUDE_FAQ=true)
- Key Terms: 5-8 items
- No years: STRICT_NO_YEARS=true
- Cozy-authority voice

Chạy: python meta_prompt_quality_agent.py [--article-id ID] [--topics] [--all]
"""

import requests
import os
import re
import json
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

# ========== SHOPIFY CONFIG ==========
SHOP = os.getenv("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-01")

HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}


# ========== META-PROMPT STANDARDS ==========
class MetaPromptStandard:
    """Tiêu chuẩn từ SHOPIFY BLOG META-PROMPT (AEO + GEO + Helpful + LLM-safe)"""

    # WORD BUDGET
    WORD_MIN = 1800
    WORD_MAX = 2200

    # CITATIONS (Sources & Further Reading)
    MIN_CITATIONS = 5  # ≥5 topic-specific primary sources (.gov/.edu/journal)
    PREFERRED_DOMAINS = [
        ".gov",
        ".edu",
        "ncbi.nlm.nih",
        "sciencedirect",
        "nature.com",
        "wiley.com",
        "springer.com",
        "pubmed",
    ]

    # EXPERT QUOTES
    MIN_QUOTES = 2  # ≥2 expert quotes with real names + titles + source

    # STATISTICS
    MIN_STATS = 3  # ≥3 quantified stats with named sources

    # STRUCTURE
    MIN_H2_COUNT = 6  # Key Conditions, Background, Framework, Varieties, Troubleshooting, Tips, FAQ, Key Terms, Sources
    REQUIRED_SECTIONS = [
        "key-conditions",
        "background",
        "framework",
        "troubleshooting",
        "expert-tips",
        "faq",
        "key-terms",
        "sources",
    ]

    # DIRECT ANSWER
    DIRECT_ANSWER_MIN_WORDS = 50
    DIRECT_ANSWER_MAX_WORDS = 70

    # FAQ
    MIN_FAQ_QUESTIONS = 5
    MAX_FAQ_QUESTIONS = 7
    FAQ_ANSWER_MIN_WORDS = 50
    FAQ_ANSWER_MAX_WORDS = 80

    # KEY TERMS
    MIN_KEY_TERMS = 5
    MAX_KEY_TERMS = 8

    # KEY CONDITIONS
    MIN_KEY_CONDITIONS = 3
    MAX_KEY_CONDITIONS = 8

    # TITLE/SEO
    TITLE_MAX_LENGTH = 70
    SEO_TITLE_MAX_LENGTH = 60
    META_DESC_MAX_LENGTH = 155

    # STRICT NO YEARS
    YEAR_PATTERN = r"\b(19|20)\d{2}\b"

    # ANCHOR IDS
    ANCHOR_ID_PATTERN = r'id="([a-z0-9\-]+)"'

    # LINKS
    LINK_PATTERN = r'<a\s+href="(https?://[^"]+)"[^>]*rel="nofollow noopener"[^>]*>'

    # IMAGE
    IMAGE_REQUIRED = True
    MIN_INLINE_IMAGES = 3


class Severity(Enum):
    CRITICAL = "🔴 CRITICAL"
    WARNING = "🟡 WARNING"
    INFO = "🔵 INFO"
    PASS = "✅ PASS"


@dataclass
class Issue:
    severity: Severity
    category: str
    message: str
    suggestion: str = ""
    meta_prompt_ref: str = ""  # Reference to META-PROMPT section


@dataclass
class QualityReport:
    article_id: int
    title: str
    url: str
    issues: List[Issue] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    score: int = 100

    @property
    def passed(self) -> bool:
        return not any(i.severity == Severity.CRITICAL for i in self.issues)

    def add_issue(self, issue: Issue):
        self.issues.append(issue)
        if issue.severity == Severity.CRITICAL:
            self.score -= 15
        elif issue.severity == Severity.WARNING:
            self.score -= 8
        elif issue.severity == Severity.INFO:
            self.score -= 3
        self.score = max(0, self.score)


class MetaPromptQualityAgent:
    """Agent kiểm tra chất lượng theo đúng META-PROMPT standards"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.std = MetaPromptStandard()

    # ==========================================
    # FETCHING
    # ==========================================

    def get_all_articles(self, limit: int = 250) -> List[dict]:
        url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles.json"
        max_page = 250
        remaining = max(limit, 0)
        params = {"limit": min(remaining, max_page)}

        articles: List[dict] = []
        while True:
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                break

            batch = response.json().get("articles", [])
            articles.extend(batch)

            if remaining:
                remaining = max(remaining - len(batch), 0)
                if remaining == 0:
                    break
            if len(batch) < max_page:
                break

            next_page_info = self._get_next_page_info(response.headers.get("Link", ""))
            if not next_page_info:
                break

            params = {
                "limit": min(remaining or max_page, max_page),
                "page_info": next_page_info,
            }

        return articles

    def _get_next_page_info(self, link_header: str) -> Optional[str]:
        if not link_header:
            return None
        for part in link_header.split(","):
            if 'rel="next"' in part:
                match = re.search(r"page_info=([^&>]+)", part)
                return match.group(1) if match else None
        return None

    def get_article(self, article_id: int) -> Optional[dict]:
        url = f"https://{SHOP}/admin/api/{API_VERSION}/articles/{article_id}.json"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json().get("article")
        return None

    # ==========================================
    # TEXT UTILITIES
    # ==========================================

    def strip_html(self, html: str) -> str:
        """Remove HTML tags"""
        if not html:
            return ""
        text = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", text).strip()

    def count_words(self, html: str) -> int:
        """Count words in HTML content"""
        text = self.strip_html(html)
        return len(text.split())

    # ==========================================
    # WORD COUNT CHECK (1800-2200)
    # ==========================================

    def check_word_count(self, html: str) -> List[Issue]:
        issues = []
        word_count = self.count_words(html)

        if word_count < self.std.WORD_MIN:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Word Count",
                    f"Chỉ có {word_count} words (cần {self.std.WORD_MIN}-{self.std.WORD_MAX})",
                    f"Thêm {self.std.WORD_MIN - word_count} words nữa",
                    "WORD_BUDGET={1800-2200}",
                )
            )
        elif word_count > self.std.WORD_MAX:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Word Count",
                    f"Có {word_count} words (vượt max {self.std.WORD_MAX})",
                    f"Cắt bớt {word_count - self.std.WORD_MAX} words",
                    "WORD_BUDGET={1800-2200}",
                )
            )
        else:
            issues.append(
                Issue(Severity.PASS, "Word Count", f"Có {word_count} words ✓")
            )

        return issues

    # ==========================================
    # CITATIONS CHECK (≥5 primary sources)
    # ==========================================

    def check_citations(self, html: str) -> List[Issue]:
        issues = []

        # Find all links with rel="nofollow noopener"
        links = re.findall(r'<a\s+href="(https?://[^"]+)"[^>]*>', html, re.IGNORECASE)

        # Count credible sources
        credible_count = 0
        for link in links:
            link_lower = link.lower()
            if any(domain in link_lower for domain in self.std.PREFERRED_DOMAINS):
                credible_count += 1

        total_links = len(links)

        if total_links < self.std.MIN_CITATIONS:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Citations",
                    f"Chỉ có {total_links} citations (cần ≥{self.std.MIN_CITATIONS})",
                    "Thêm sources từ .gov/.edu/journal/NCBI",
                    "Citations: ≥5 topic-specific primary sources",
                )
            )
        else:
            issues.append(
                Issue(Severity.PASS, "Citations", f"Có {total_links} citations ✓")
            )

        if credible_count == 0 and total_links > 0:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Citations",
                    "Không có sources từ .gov/.edu/journal",
                    "Thêm ít nhất 2-3 sources từ nguồn học thuật",
                    "Preferred: .gov/.edu/journal",
                )
            )

        return issues

    # ==========================================
    # EXPERT QUOTES CHECK (≥2)
    # ==========================================

    def check_expert_quotes(self, html: str) -> List[Issue]:
        issues = []

        # Method 1: Find blockquotes with attribution
        blockquotes = re.findall(
            r"<blockquote[^>]*>(.*?)</blockquote>", html, re.DOTALL | re.IGNORECASE
        )
        proper_quotes = 0
        for bq in blockquotes:
            if re.search(r"—\s*[A-Z][a-z]+.*,", bq) or re.search(
                r"–\s*[A-Z][a-z]+.*,", bq
            ):
                proper_quotes += 1

        # Method 2: Find inline expert quotes in <p> tags
        # Pattern: "Dr./Professor Name, Title, explains:/notes:/advises:"
        expert_patterns = [
            r"Dr\.\s+[A-Z][a-z]+\s+[A-Z][a-z]+[^<]*(?:explains|notes|advises|observes|states|shares):",
            r"Professor\s+[A-Z][a-z]+\s+[A-Z][a-z]+[^<]*(?:explains|notes|advises|observes|states|shares):",
            r"Chef\s+[A-Z][a-z]+\s+[A-Z][a-z]+[^<]*(?:explains|notes|advises|observes|states|shares):",
            r"[A-Z][a-z]+\s+[A-Z][a-z]+,\s+(?:Expert|Author|Specialist|Professor|Director|Founder)[^<]*(?:explains|notes|advises|observes|states|shares):",
        ]
        for pattern in expert_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            proper_quotes += len(matches)

        if proper_quotes < self.std.MIN_QUOTES:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Expert Quotes",
                    f"Chỉ có {proper_quotes} expert quotes (cần ≥{self.std.MIN_QUOTES})",
                    'Thêm quotes format: <blockquote>"Quote" — Name, Title, Org</blockquote>',
                    "Quotes: ≥2 expert quotes with real names + titles + source",
                )
            )
        else:
            issues.append(
                Issue(
                    Severity.PASS,
                    "Expert Quotes",
                    f"Có {proper_quotes} expert quotes ✓",
                )
            )

        return issues

    # ==========================================
    # STATISTICS CHECK (≥3)
    # ==========================================

    def check_statistics(self, html: str) -> List[Issue]:
        issues = []
        text = self.strip_html(html)

        # Find patterns like: "X%" or "X million" or "X billion" or numbers with context
        stat_patterns = [
            r"\d+(?:\.\d+)?%",  # Percentages
            r"\d+(?:\.\d+)?\s*(?:million|billion|trillion)",  # Large numbers
            r"\$\d+(?:\.\d+)?(?:\s*(?:million|billion|trillion))?",  # Money
            r"\d+(?:,\d{3})+",  # Numbers with commas
            r"(?:approximately|about|around|over|under|nearly)\s+\d+",  # Approximate numbers
        ]

        stats_found = 0
        for pattern in stat_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            stats_found += len(matches)

        if stats_found < self.std.MIN_STATS:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Statistics",
                    f"Chỉ có ~{stats_found} statistics (cần ≥{self.std.MIN_STATS})",
                    "Thêm stats với số liệu cụ thể + nguồn",
                    "Statistics: ≥3 quantified stats with named sources",
                )
            )
        else:
            issues.append(
                Issue(Severity.PASS, "Statistics", f"Có ~{stats_found} statistics ✓")
            )

        return issues

    # ==========================================
    # STRUCTURE CHECK (H2/H3 sections)
    # ==========================================

    def check_structure(self, html: str) -> List[Issue]:
        issues = []

        # Count H2 headings
        h2_matches = re.findall(r'<h2[^>]*id="([^"]*)"[^>]*>', html, re.IGNORECASE)
        h2_count = len(re.findall(r"<h2[^>]*>", html, re.IGNORECASE))

        if h2_count < self.std.MIN_H2_COUNT:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Structure",
                    f"Chỉ có {h2_count} H2 sections (recommend ≥{self.std.MIN_H2_COUNT})",
                    "Thêm sections: Key Conditions, Background, Framework, Troubleshooting, Expert Tips, FAQ, Key Terms, Sources",
                    "Required sections per META-PROMPT",
                )
            )
        else:
            issues.append(
                Issue(Severity.PASS, "Structure", f"Có {h2_count} H2 sections ✓")
            )

        # Check for required section IDs
        missing_sections = []
        for section_id in self.std.REQUIRED_SECTIONS:
            if section_id not in html.lower():
                missing_sections.append(section_id)

        if missing_sections:
            issues.append(
                Issue(
                    Severity.INFO,
                    "Structure",
                    f"Thiếu sections: {', '.join(missing_sections[:3])}...",
                    "Thêm các sections theo cấu trúc META-PROMPT",
                )
            )

        # Check for unique kebab-case IDs
        all_ids = re.findall(r'id="([^"]+)"', html)
        duplicate_ids = [id for id in all_ids if all_ids.count(id) > 1]

        if duplicate_ids:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Structure",
                    f"Có ID trùng lặp: {set(duplicate_ids)}",
                    "Đảm bảo mỗi H2/H3 có unique kebab-case id",
                    "All H2/H3 must have unique kebab-case ids",
                )
            )

        return issues

    # ==========================================
    # DIRECT ANSWER CHECK (50-70 words)
    # ==========================================

    def check_direct_answer(self, html: str) -> List[Issue]:
        issues = []

        # Find first paragraph with "Direct Answer" or opening paragraph
        da_match = re.search(
            r"<p><strong>Direct Answer:?</strong>\s*(.*?)</p>",
            html,
            re.IGNORECASE | re.DOTALL,
        )

        if not da_match:
            # Check first paragraph
            first_p = re.search(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
            if first_p:
                da_text = self.strip_html(first_p.group(1))
                da_words = len(da_text.split())

                if da_words < self.std.DIRECT_ANSWER_MIN_WORDS:
                    issues.append(
                        Issue(
                            Severity.INFO,
                            "Direct Answer",
                            f"Opening paragraph có {da_words} words (recommend {self.std.DIRECT_ANSWER_MIN_WORDS}-{self.std.DIRECT_ANSWER_MAX_WORDS})",
                            "Thêm <strong>Direct Answer:</strong> 50-70 words ở đầu",
                            "Direct answer first: 50-70 words at the top",
                        )
                    )
            else:
                issues.append(
                    Issue(
                        Severity.WARNING,
                        "Direct Answer",
                        "Không tìm thấy Direct Answer section",
                        "Thêm <p><strong>Direct Answer:</strong> ... </p> ở đầu bài",
                    )
                )
        else:
            da_text = self.strip_html(da_match.group(1))
            da_words = len(da_text.split())

            if (
                da_words < self.std.DIRECT_ANSWER_MIN_WORDS
                or da_words > self.std.DIRECT_ANSWER_MAX_WORDS
            ):
                issues.append(
                    Issue(
                        Severity.INFO,
                        "Direct Answer",
                        f"Direct Answer có {da_words} words (cần {self.std.DIRECT_ANSWER_MIN_WORDS}-{self.std.DIRECT_ANSWER_MAX_WORDS})",
                        "Điều chỉnh độ dài Direct Answer",
                    )
                )
            else:
                issues.append(
                    Issue(
                        Severity.PASS,
                        "Direct Answer",
                        f"Direct Answer có {da_words} words ✓",
                    )
                )

        return issues

    # ==========================================
    # FAQ CHECK (5-7 questions)
    # ==========================================

    def check_faq(self, html: str) -> List[Issue]:
        issues = []

        # Find FAQ section
        faq_section = re.search(
            r'<h2[^>]*id="faq"[^>]*>.*?(?=<h2|$)', html, re.IGNORECASE | re.DOTALL
        )

        if not faq_section:
            faq_section = re.search(
                r"<h2[^>]*>.*?FAQ.*?</h2>.*?(?=<h2|$)", html, re.IGNORECASE | re.DOTALL
            )

        if not faq_section:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "FAQ",
                    "Không tìm thấy FAQ section",
                    'Thêm <h2 id="faq">FAQ</h2> với 5-7 questions',
                    "Provide 5-7 FAQs if INCLUDE_FAQ=true",
                )
            )
        else:
            # Count H3 questions in FAQ
            faq_content = faq_section.group(0)
            faq_questions = len(re.findall(r"<h3[^>]*>", faq_content, re.IGNORECASE))

            if faq_questions < self.std.MIN_FAQ_QUESTIONS:
                issues.append(
                    Issue(
                        Severity.WARNING,
                        "FAQ",
                        f"FAQ chỉ có {faq_questions} questions (cần {self.std.MIN_FAQ_QUESTIONS}-{self.std.MAX_FAQ_QUESTIONS})",
                        f"Thêm {self.std.MIN_FAQ_QUESTIONS - faq_questions} FAQ questions nữa",
                    )
                )
            elif faq_questions > self.std.MAX_FAQ_QUESTIONS:
                issues.append(
                    Issue(
                        Severity.INFO,
                        "FAQ",
                        f"FAQ có {faq_questions} questions (max recommend: {self.std.MAX_FAQ_QUESTIONS})",
                        "Có thể giảm bớt FAQ questions",
                    )
                )
            else:
                issues.append(
                    Issue(Severity.PASS, "FAQ", f"FAQ có {faq_questions} questions ✓")
                )

        return issues

    # ==========================================
    # KEY TERMS CHECK (5-8 items)
    # ==========================================

    def check_key_terms(self, html: str) -> List[Issue]:
        issues = []

        # Find Key Terms section
        kt_section = re.search(
            r'<h2[^>]*id="key-terms"[^>]*>.*?(?=<h2|$)', html, re.IGNORECASE | re.DOTALL
        )

        if not kt_section:
            kt_section = re.search(
                r"<h2[^>]*>.*?Key Terms.*?</h2>.*?(?=<h2|$)",
                html,
                re.IGNORECASE | re.DOTALL,
            )

        if not kt_section:
            issues.append(
                Issue(
                    Severity.INFO,
                    "Key Terms",
                    "Không tìm thấy Key Terms section",
                    'Thêm <h2 id="key-terms">Key Terms</h2> với 5-8 terms',
                    "Key terms: 5-8 items with scientific/common names",
                )
            )
        else:
            # Count list items
            kt_content = kt_section.group(0)
            kt_items = len(re.findall(r"<li[^>]*>", kt_content, re.IGNORECASE))

            if kt_items < self.std.MIN_KEY_TERMS:
                issues.append(
                    Issue(
                        Severity.INFO,
                        "Key Terms",
                        f"Key Terms chỉ có {kt_items} items (cần {self.std.MIN_KEY_TERMS}-{self.std.MAX_KEY_TERMS})",
                        f"Thêm {self.std.MIN_KEY_TERMS - kt_items} key terms nữa",
                    )
                )
            else:
                issues.append(
                    Issue(
                        Severity.PASS, "Key Terms", f"Key Terms có {kt_items} items ✓"
                    )
                )

        return issues

    # ==========================================
    # NO YEARS CHECK (STRICT_NO_YEARS)
    # ==========================================

    def check_no_years(self, article: dict) -> List[Issue]:
        issues = []

        # Check title, meta, and body for years
        title = article.get("title", "")
        html = article.get("body_html", "")
        summary = article.get("summary_html", "") or ""

        all_text = f"{title} {html} {summary}"
        years_found = re.findall(self.std.YEAR_PATTERN, all_text)

        if years_found:
            unique_years = list(
                set(["".join(y) if isinstance(y, tuple) else y for y in years_found])
            )
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "No Years",
                    f"Tìm thấy years: {unique_years[:5]}",
                    "Xóa tất cả years (STRICT_NO_YEARS=true)",
                    "STRICT_NO_YEARS={true} # ban years across all fields",
                )
            )
        else:
            issues.append(
                Issue(Severity.PASS, "No Years", "Không có years trong content ✓")
            )

        return issues

    # ==========================================
    # TITLE & SEO CHECK
    # ==========================================

    def check_title_seo(self, article: dict) -> List[Issue]:
        issues = []

        title = article.get("title", "")

        if len(title) > self.std.TITLE_MAX_LENGTH:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Title",
                    f"Title quá dài: {len(title)} chars (max {self.std.TITLE_MAX_LENGTH})",
                    "Rút gọn title",
                )
            )

        # Check for numeric prefix
        if re.match(r"^\d+[\.\):]", title):
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Title",
                    "Title bắt đầu bằng số",
                    "Xóa numeric prefix",
                    "TITLE: no numeric prefix",
                )
            )
        else:
            issues.append(
                Issue(Severity.PASS, "Title", f"Title format OK ({len(title)} chars) ✓")
            )

        return issues

    # ==========================================
    # IMAGE CHECK
    # ==========================================

    def check_image(self, article: dict) -> List[Issue]:
        issues = []

        image = article.get("image")
        html = article.get("body_html", "")

        img_tags = re.findall(r"<img\b[^>]*>", html, re.IGNORECASE)
        inline_count = len(img_tags)
        inline_missing_alt = 0
        for tag in img_tags:
            alt_match = re.search(r"\balt=\"([^\"]*)\"", tag, re.IGNORECASE)
            if not alt_match or not alt_match.group(1).strip():
                inline_missing_alt += 1

        if inline_count < self.std.MIN_INLINE_IMAGES:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Image",
                    f"Inline images quá ít ({inline_count}/{self.std.MIN_INLINE_IMAGES})",
                    "Thêm đủ 3 inline images trong body",
                )
            )
        else:
            issues.append(
                Issue(
                    Severity.PASS,
                    "Image",
                    f"Inline images đủ ({inline_count}) ✓",
                )
            )

        if inline_missing_alt > 0:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Image",
                    f"Inline images thiếu alt ({inline_missing_alt})",
                    "Thêm alt text cho tất cả inline images",
                )
            )
        else:
            if inline_count > 0:
                issues.append(
                    Issue(
                        Severity.PASS,
                        "Image",
                        "Inline images có alt text ✓",
                    )
                )

        if not image:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Image",
                    "Không có featured image",
                    "Thêm featured image",
                )
            )
        else:
            alt = image.get("alt", "")
            if not alt:
                issues.append(
                    Issue(
                        Severity.WARNING,
                        "Image",
                        "Image không có alt text",
                        "Thêm descriptive alt text",
                    )
                )
            else:
                issues.append(
                    Issue(Severity.PASS, "Image", "Có featured image với alt text ✓")
                )

        return issues

    # ==========================================
    # MAIN AUDIT
    # ==========================================

    def audit_article(self, article: dict) -> QualityReport:
        """Audit toàn diện theo META-PROMPT standards"""

        report = QualityReport(
            article_id=article["id"],
            title=article.get("title", "Untitled"),
            url=f"https://therike.com/blogs/sustainable-living/{article.get('handle', '')}",
        )

        html = article.get("body_html", "")

        # Collect metrics
        report.metrics = {
            "word_count": self.count_words(html),
            "h2_count": len(re.findall(r"<h2[^>]*>", html, re.IGNORECASE)),
            "links_count": len(
                re.findall(r'<a\s+href="https?://', html, re.IGNORECASE)
            ),
            "blockquotes": len(re.findall(r"<blockquote", html, re.IGNORECASE)),
            "inline_images": len(re.findall(r"<img\b[^>]*>", html, re.IGNORECASE)),
            "inline_images_missing_alt": len(
                [
                    tag
                    for tag in re.findall(r"<img\b[^>]*>", html, re.IGNORECASE)
                    if not re.search(r"\balt=\"[^\"]*\S[^\"]*\"", tag, re.IGNORECASE)
                ]
            ),
        }

        # Run all checks according to META-PROMPT
        all_issues = []
        all_issues.extend(self.check_word_count(html))
        all_issues.extend(self.check_citations(html))
        all_issues.extend(self.check_expert_quotes(html))
        all_issues.extend(self.check_statistics(html))
        all_issues.extend(self.check_structure(html))
        all_issues.extend(self.check_direct_answer(html))
        all_issues.extend(self.check_faq(html))
        all_issues.extend(self.check_key_terms(html))
        all_issues.extend(self.check_no_years(article))
        all_issues.extend(self.check_title_seo(article))
        all_issues.extend(self.check_image(article))

        for issue in all_issues:
            report.add_issue(issue)

        return report

    def audit_all(self, article_ids: List[int] = None) -> List[QualityReport]:
        if article_ids:
            articles = [self.get_article(aid) for aid in article_ids]
            articles = [a for a in articles if a]
        else:
            articles = self.get_all_articles()

        return [self.audit_article(a) for a in articles]

    # ==========================================
    # REPORTING
    # ==========================================

    def print_report(self, report: QualityReport, verbose: bool = True):
        status = "✅ PASS" if report.passed else "❌ FAIL"
        print(f"\n{'='*70}")
        print(f"{status} [{report.score}/100] {report.title[:50]}...")
        print(f"ID: {report.article_id}")
        print(f"{'='*70}")

        # Print metrics
        m = report.metrics
        print(
            f"📊 Words: {m.get('word_count', 0)} | H2s: {m.get('h2_count', 0)} | Links: {m.get('links_count', 0)} | Quotes: {m.get('blockquotes', 0)}"
        )

        if verbose:
            categories = {}
            for issue in report.issues:
                cat = issue.category
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(issue)

            for cat, issues in categories.items():
                print(f"\n📋 {cat}:")
                for issue in issues:
                    print(f"   {issue.severity.value} {issue.message}")
                    if issue.suggestion and issue.severity != Severity.PASS:
                        print(f"      💡 {issue.suggestion}")
                    if issue.meta_prompt_ref:
                        print(f"      📖 META-PROMPT: {issue.meta_prompt_ref}")

    def print_summary(self, reports: List[QualityReport]):
        passed = [r for r in reports if r.passed]
        failed = [r for r in reports if not r.passed]
        avg_score = sum(r.score for r in reports) / len(reports) if reports else 0

        print("\n")
        print("=" * 70)
        print("📊 META-PROMPT QUALITY AGENT - TỔNG KẾT")
        print("=" * 70)
        print(
            f"📈 Tổng: {len(reports)} bài | ✅ {len(passed)} pass | ❌ {len(failed)} fail"
        )
        print(f"📊 Điểm TB: {avg_score:.1f}/100")
        print(
            f"📊 Tỷ lệ pass: {len(passed)*100/len(reports):.1f}%" if reports else "N/A"
        )

        # META-PROMPT compliance summary
        print("\n📋 META-PROMPT COMPLIANCE:")
        total_words = sum(r.metrics.get("word_count", 0) for r in reports)
        avg_words = total_words / len(reports) if reports else 0
        print(f"   📝 Avg Words: {avg_words:.0f} (target: 1800-2200)")

        total_inline = sum(r.metrics.get("inline_images", 0) for r in reports)
        avg_inline = total_inline / len(reports) if reports else 0
        total_missing_alt = sum(
            r.metrics.get("inline_images_missing_alt", 0) for r in reports
        )
        print(
            f"   🖼️ Avg Inline Images: {avg_inline:.1f} (target: {self.std.MIN_INLINE_IMAGES})"
        )
        print(f"   🏷️ Inline Images Missing Alt: {total_missing_alt}")

        # Critical issues
        if failed:
            print(f"\n❌ BÀI KHÔNG ĐẠT ({len(failed)}):")
            failed.sort(key=lambda r: r.score)
            for r in failed[:10]:
                critical = [i for i in r.issues if i.severity == Severity.CRITICAL]
                print(f"   [{r.score:2d}] {r.title[:40]}...")
                for c in critical[:3]:
                    print(f"       🔴 {c.category}: {c.message[:50]}")

        if passed:
            print(f"\n✅ BÀI ĐẠT CHUẨN ({len(passed)}):")
            for r in sorted(passed, key=lambda x: -x.score)[:5]:
                print(f"   [{r.score:3d}] {r.title[:50]}...")

    def export_report(self, reports: List[QualityReport], filename: str = None):
        if not filename:
            filename = f"meta_prompt_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        data = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total": len(reports),
                "passed": len([r for r in reports if r.passed]),
                "failed": len([r for r in reports if not r.passed]),
                "avg_score": (
                    sum(r.score for r in reports) / len(reports) if reports else 0
                ),
            },
            "articles": [
                {
                    "id": r.article_id,
                    "title": r.title,
                    "url": r.url,
                    "score": r.score,
                    "passed": r.passed,
                    "metrics": r.metrics,
                    "issues": [
                        {
                            "severity": i.severity.name,
                            "category": i.category,
                            "message": i.message,
                            "suggestion": i.suggestion,
                            "meta_prompt_ref": i.meta_prompt_ref,
                        }
                        for i in r.issues
                    ],
                }
                for r in reports
            ],
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n📁 Đã export báo cáo: {filename}")
        return filename


def main():
    parser = argparse.ArgumentParser(description="META-PROMPT Quality Agent")
    parser.add_argument("--article-id", "-a", type=int, help="Audit single article")
    parser.add_argument(
        "--topics", "-t", action="store_true", help="Audit Topics 21-33"
    )
    parser.add_argument("--all", action="store_true", help="Audit all articles")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--limit", "-l", type=int, default=50, help="Limit articles")
    parser.add_argument(
        "--export", "-e", action="store_true", help="Export report JSON"
    )

    args = parser.parse_args()

    print("🤖 META-PROMPT QUALITY AGENT")
    print("=" * 70)
    print("📋 Kiểm tra theo ĐÚNG tiêu chuẩn META-PROMPT:")
    print("   • WORD_BUDGET: 1800-2200")
    print("   • Citations: ≥5 (.gov/.edu/journal)")
    print("   • Expert Quotes: ≥2")
    print("   • Statistics: ≥3")
    print("   • FAQ: 5-7 questions")
    print("   • Key Terms: 5-8 items")
    print("   • STRICT_NO_YEARS: true")
    print("=" * 70)

    agent = MetaPromptQualityAgent()

    TOPICS_21_33 = [
        690501058878,
        690500337982,
        690499584318,
        690499518782,
        690501091646,
        690501124414,
        690501157182,
        690501189950,
        690501222718,
        690502697278,
        690503254334,
        690504433982,
        690504499518,
    ]

    if args.article_id:
        article = agent.get_article(args.article_id)
        if article:
            report = agent.audit_article(article)
            agent.print_report(report, verbose=True)
        else:
            print(f"❌ Không tìm thấy article ID {args.article_id}")

    elif args.topics:
        print(f"\n📋 Audit Topics 21-33 ({len(TOPICS_21_33)} bài)...")
        reports = agent.audit_all(TOPICS_21_33)

        if args.verbose:
            for r in reports:
                agent.print_report(r, verbose=True)

        agent.print_summary(reports)

        if args.export:
            agent.export_report(reports)

    else:
        print(f"\n📋 Audit all articles (limit: {args.limit})...")
        articles = agent.get_all_articles(limit=args.limit)
        reports = [agent.audit_article(a) for a in articles]

        if args.verbose:
            for r in reports:
                agent.print_report(r, verbose=True)

        agent.print_summary(reports)

        if args.export:
            agent.export_report(reports)


if __name__ == "__main__":
    main()
