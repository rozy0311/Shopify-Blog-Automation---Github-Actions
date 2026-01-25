#!/usr/bin/env python3
"""
🤖 QUALITY AGENT - Tự động kiểm tra chất lượng nội dung blog
Dựa trên META-PROMPT standards trong agent_memory.yaml

Chạy: python quality_agent.py [--fix] [--article-id ID]
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


# ========== QUALITY STANDARDS (từ META-PROMPT) ==========
class QualityStandard:
    # Title
    TITLE_MAX_LENGTH = 70
    TITLE_KEYWORD_POSITION = 10  # Keyword trong 10 ký tự đầu
    TITLE_REQUIRES_COLON = True
    TITLE_NO_YEAR = True
    TITLE_NO_NUMERIC_PREFIX = True

    # Hidden Links
    MIN_HIDDEN_LINKS = 2
    RECOMMENDED_LINKS = 5
    LINK_PATTERN = (
        r'<a\s+href="https?://[^"]+"\s+target="_blank"\s+rel="noopener">[^<]+</a>'
    )
    RAW_URL_PATTERN = r'(?<!["\'])https?://[^\s<>"\']+(?!["\'])'

    # Content Structure
    MIN_H2_COUNT = 2
    MIN_WORD_COUNT = 500
    MIN_PARAGRAPHS = 3

    # Image
    IMAGE_REQUIRED = True


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
    auto_fixable: bool = False


@dataclass
class QualityReport:
    article_id: int
    title: str
    url: str
    issues: List[Issue] = field(default_factory=list)
    score: int = 100

    @property
    def passed(self) -> bool:
        return not any(i.severity == Severity.CRITICAL for i in self.issues)

    def add_issue(self, issue: Issue):
        self.issues.append(issue)
        if issue.severity == Severity.CRITICAL:
            self.score -= 25
        elif issue.severity == Severity.WARNING:
            self.score -= 10
        elif issue.severity == Severity.INFO:
            self.score -= 5
        self.score = max(0, self.score)


class QualityAgent:
    """Agent tự động kiểm tra chất lượng blog content"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ==========================================
    # FETCHING
    # ==========================================

    def get_all_articles(self, limit: int = 250) -> List[dict]:
        """Lấy tất cả articles (có phân trang)"""
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
        """Parse Shopify REST Link header for next page_info"""
        if not link_header:
            return None
        for part in link_header.split(","):
            if 'rel="next"' in part:
                match = re.search(r"page_info=([^&>]+)", part)
                return match.group(1) if match else None
        return None

    def get_article(self, article_id: int) -> Optional[dict]:
        """Lấy 1 article"""
        url = f"https://{SHOP}/admin/api/{API_VERSION}/articles/{article_id}.json"
        response = self.session.get(url)
        if response.status_code == 200:
            return response.json().get("article")
        return None

    # ==========================================
    # TITLE CHECKS
    # ==========================================

    def check_title(self, title: str) -> List[Issue]:
        """Kiểm tra title theo META-PROMPT standards"""
        issues = []

        if not title:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Title",
                    "Không có title",
                    "Thêm title với format: 'Primary Keyword: How to X'",
                )
            )
            return issues

        # Check length
        if len(title) > QualityStandard.TITLE_MAX_LENGTH:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Title",
                    f"Title quá dài ({len(title)} chars, max {QualityStandard.TITLE_MAX_LENGTH})",
                    "Rút gọn title để hiển thị tốt trên search results",
                )
            )

        # Check for year (bad practice)
        if re.search(r"\b20\d{2}\b", title):
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Title",
                    "Title chứa năm (sẽ outdated nhanh)",
                    "Xóa năm khỏi title để content evergreen",
                    auto_fixable=True,
                )
            )

        # Check for numeric prefix
        if re.match(r"^\d+[\.\):]", title):
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Title",
                    "Title bắt đầu bằng số",
                    "Xóa số prefix, đưa keyword lên đầu",
                )
            )

        # Check for colon separator
        if ":" not in title:
            issues.append(
                Issue(
                    Severity.INFO,
                    "Title",
                    "Title không có dấu ':' phân tách keyword và payoff",
                    "Dùng format: 'Primary Keyword: Clear Benefit/How-to'",
                )
            )
        else:
            # Check keyword position
            keyword_part = title.split(":")[0].strip()
            if len(keyword_part) > 30:
                issues.append(
                    Issue(
                        Severity.INFO,
                        "Title",
                        f"Keyword phrase quá dài ({len(keyword_part)} chars)",
                        "Đưa primary keyword vào đầu title",
                    )
                )

        if not issues:
            issues.append(Issue(Severity.PASS, "Title", "Title đạt chuẩn"))

        return issues

    # ==========================================
    # HIDDEN LINKS CHECKS
    # ==========================================

    def check_hidden_links(self, html: str) -> List[Issue]:
        """Kiểm tra hidden links theo standards"""
        issues = []

        if not html:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Links",
                    "Không có nội dung HTML",
                    "Cần republish bài với nội dung đầy đủ",
                )
            )
            return issues

        # Count proper hidden links
        proper_links = re.findall(QualityStandard.LINK_PATTERN, html, re.IGNORECASE)
        link_count = len(proper_links)

        # Check for raw URLs (bad practice)
        # Exclude URLs inside href attributes
        text_without_hrefs = re.sub(r'href="[^"]+"', "", html)
        raw_urls = re.findall(QualityStandard.RAW_URL_PATTERN, text_without_hrefs)

        if raw_urls:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Links",
                    f"Có {len(raw_urls)} raw URLs hiển thị trong text",
                    'Chuyển thành hidden links: <a href="URL" target="_blank" rel="noopener">Source Name</a>',
                    auto_fixable=True,
                )
            )

        # Check link count
        if link_count == 0:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Links",
                    "Không có hidden links",
                    f"Cần thêm ít nhất {QualityStandard.MIN_HIDDEN_LINKS} hidden links với credible sources",
                    auto_fixable=False,
                )
            )
        elif link_count < QualityStandard.MIN_HIDDEN_LINKS:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Links",
                    f"Chỉ có {link_count}/{QualityStandard.MIN_HIDDEN_LINKS} hidden links",
                    "Thêm hidden links từ sources uy tín (.gov, .edu, research)",
                )
            )
        elif link_count < QualityStandard.RECOMMENDED_LINKS:
            issues.append(
                Issue(
                    Severity.INFO,
                    "Links",
                    f"Có {link_count} links (recommend {QualityStandard.RECOMMENDED_LINKS}+)",
                    "Có thể thêm links để tăng credibility",
                )
            )
        else:
            issues.append(
                Issue(Severity.PASS, "Links", f"Có {link_count} hidden links")
            )

        # Check link quality (domains)
        credible_domains = [
            ".gov",
            ".edu",
            ".org",
            "ncbi.nlm.nih",
            "sciencedirect",
            "nature.com",
        ]
        credible_count = sum(
            1
            for link in proper_links
            if any(d in link.lower() for d in credible_domains)
        )

        if link_count > 0 and credible_count == 0:
            issues.append(
                Issue(
                    Severity.INFO,
                    "Links",
                    "Không có links từ nguồn .gov/.edu/.org",
                    "Thêm links từ sources học thuật/chính phủ để tăng authority",
                )
            )

        return issues

    # ==========================================
    # CONTENT STRUCTURE CHECKS
    # ==========================================

    def check_structure(self, html: str) -> List[Issue]:
        """Kiểm tra cấu trúc content"""
        issues = []

        if not html:
            return [Issue(Severity.CRITICAL, "Structure", "Không có nội dung")]

        # Count H2 headings
        h2_count = len(re.findall(r"<h2[^>]*>", html, re.IGNORECASE))

        if h2_count == 0:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Structure",
                    "Không có H2 headings",
                    "Thêm ít nhất 2 H2 để chia sections",
                )
            )
        elif h2_count < QualityStandard.MIN_H2_COUNT:
            issues.append(
                Issue(
                    Severity.WARNING,
                    "Structure",
                    f"Chỉ có {h2_count} H2 (cần {QualityStandard.MIN_H2_COUNT}+)",
                    "Thêm H2 headings để improve readability",
                )
            )
        else:
            issues.append(
                Issue(Severity.PASS, "Structure", f"Có {h2_count} H2 headings")
            )

        # Count words (strip HTML)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        word_count = len(text.split())

        if word_count < QualityStandard.MIN_WORD_COUNT:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Structure",
                    f"Content quá ngắn ({word_count} words, cần {QualityStandard.MIN_WORD_COUNT}+)",
                    "Thêm nội dung chi tiết hơn",
                )
            )
        else:
            issues.append(Issue(Severity.PASS, "Structure", f"Có {word_count} words"))

        # Check for lists (actionable content)
        has_lists = bool(re.search(r"<[uo]l[^>]*>", html, re.IGNORECASE))
        if not has_lists:
            issues.append(
                Issue(
                    Severity.INFO,
                    "Structure",
                    "Không có bullet/numbered lists",
                    "Thêm lists cho actionable steps",
                )
            )

        # Check paragraphs
        p_count = len(re.findall(r"<p[^>]*>", html, re.IGNORECASE))
        if p_count < QualityStandard.MIN_PARAGRAPHS:
            issues.append(
                Issue(
                    Severity.INFO,
                    "Structure",
                    f"Ít paragraphs ({p_count})",
                    "Chia nội dung thành nhiều đoạn hơn",
                )
            )

        return issues

    # ==========================================
    # IMAGE CHECKS
    # ==========================================

    def check_image(self, article: dict) -> List[Issue]:
        """Kiểm tra featured image"""
        issues = []

        image = article.get("image")

        if not image:
            issues.append(
                Issue(
                    Severity.CRITICAL,
                    "Image",
                    "Không có featured image",
                    "Thêm image từ Pexels API",
                    auto_fixable=True,
                )
            )
        else:
            # Check alt text
            alt = image.get("alt", "")
            if not alt:
                issues.append(
                    Issue(
                        Severity.WARNING,
                        "Image",
                        "Image không có alt text",
                        "Thêm alt text mô tả image cho SEO",
                    )
                )
            else:
                issues.append(
                    Issue(Severity.PASS, "Image", "Có featured image với alt text")
                )

        return issues

    # ==========================================
    # SEO CHECKS
    # ==========================================

    def check_seo(self, article: dict) -> List[Issue]:
        """Kiểm tra SEO elements"""
        issues = []

        # Check meta description
        summary = article.get("summary_html", "") or ""
        if not summary or len(summary) < 50:
            issues.append(
                Issue(
                    Severity.INFO,
                    "SEO",
                    "Không có hoặc quá ngắn summary/excerpt",
                    "Thêm meta description 120-160 chars",
                )
            )

        # Check handle/URL
        handle = article.get("handle", "")
        if handle:
            if len(handle) > 60:
                issues.append(
                    Issue(
                        Severity.INFO, "SEO", "URL handle quá dài", "Rút gọn URL slug"
                    )
                )
            if re.search(r"[^a-z0-9\-]", handle):
                issues.append(
                    Issue(
                        Severity.WARNING,
                        "SEO",
                        "URL handle có ký tự đặc biệt",
                        "Chỉ dùng lowercase letters, numbers, hyphens",
                    )
                )

        return issues

    # ==========================================
    # MAIN AUDIT
    # ==========================================

    def audit_article(self, article: dict) -> QualityReport:
        """Audit toàn diện 1 article"""
        report = QualityReport(
            article_id=article["id"],
            title=article.get("title", "Untitled"),
            url=f"https://therike.com/blogs/sustainable-living/{article.get('handle', '')}",
        )

        # Run all checks
        html = article.get("body_html", "")

        report.issues.extend(self.check_title(article.get("title", "")))
        report.issues.extend(self.check_hidden_links(html))
        report.issues.extend(self.check_structure(html))
        report.issues.extend(self.check_image(article))
        report.issues.extend(self.check_seo(article))

        # Calculate score
        for issue in report.issues:
            if issue.severity == Severity.CRITICAL:
                report.score -= 25
            elif issue.severity == Severity.WARNING:
                report.score -= 10
            elif issue.severity == Severity.INFO:
                report.score -= 3
        report.score = max(0, report.score)

        return report

    def audit_all(self, article_ids: List[int] = None) -> List[QualityReport]:
        """Audit nhiều articles"""
        if article_ids:
            articles = [self.get_article(aid) for aid in article_ids]
            articles = [a for a in articles if a]
        else:
            articles = self.get_all_articles()

        reports = []
        for article in articles:
            report = self.audit_article(article)
            reports.append(report)

        return reports

    # ==========================================
    # REPORTING
    # ==========================================

    def print_report(self, report: QualityReport, verbose: bool = True):
        """Print báo cáo 1 article"""
        status = "✅ PASS" if report.passed else "❌ FAIL"
        print(f"\n{'='*70}")
        print(f"{status} [{report.score}/100] {report.title[:50]}...")
        print(f"ID: {report.article_id} | URL: {report.url}")
        print(f"{'='*70}")

        if verbose:
            # Group by category
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

    def print_summary(self, reports: List[QualityReport]):
        """Print tổng kết"""
        passed = [r for r in reports if r.passed]
        failed = [r for r in reports if not r.passed]
        avg_score = sum(r.score for r in reports) / len(reports) if reports else 0

        print("\n")
        print("=" * 70)
        print("📊 QUALITY AGENT - TỔNG KẾT")
        print("=" * 70)
        print(
            f"📈 Tổng: {len(reports)} bài | ✅ {len(passed)} pass | ❌ {len(failed)} fail"
        )
        print(f"📊 Điểm TB: {avg_score:.1f}/100")
        print(
            f"📊 Tỷ lệ pass: {len(passed)*100/len(reports):.1f}%" if reports else "N/A"
        )

        if failed:
            print(f"\n❌ BÀI CẦN SỬA ({len(failed)}):")
            # Sort by score
            failed.sort(key=lambda r: r.score)
            for r in failed[:10]:  # Top 10 worst
                critical_issues = [
                    i for i in r.issues if i.severity == Severity.CRITICAL
                ]
                issue_summary = ", ".join([i.category for i in critical_issues])
                print(f"   [{r.score:2d}] ID {r.article_id}: {r.title[:35]}...")
                print(f"       Issues: {issue_summary}")

        if passed:
            print(f"\n✅ BÀI ĐẠT CHUẨN ({len(passed)}):")
            for r in passed[:5]:  # Top 5
                print(f"   [{r.score:3d}] {r.title[:50]}...")

        # Common issues
        all_issues = [
            i
            for r in reports
            for i in r.issues
            if i.severity in [Severity.CRITICAL, Severity.WARNING]
        ]
        issue_counts = {}
        for i in all_issues:
            key = f"{i.category}: {i.message[:40]}"
            issue_counts[key] = issue_counts.get(key, 0) + 1

        if issue_counts:
            print("\n📌 VẤN ĐỀ PHỔ BIẾN:")
            for msg, count in sorted(issue_counts.items(), key=lambda x: -x[1])[:5]:
                print(f"   {count}x - {msg}")

    def export_report(self, reports: List[QualityReport], filename: str = None):
        """Export báo cáo ra JSON"""
        if not filename:
            filename = f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

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
                    "issues": [
                        {
                            "severity": i.severity.name,
                            "category": i.category,
                            "message": i.message,
                            "suggestion": i.suggestion,
                            "auto_fixable": i.auto_fixable,
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


# ==========================================
# MAIN
# ==========================================


def main():
    parser = argparse.ArgumentParser(
        description="Quality Agent - Kiểm tra chất lượng blog"
    )
    parser.add_argument("--article-id", "-a", type=int, help="Audit 1 article cụ thể")
    parser.add_argument(
        "--topics", "-t", action="store_true", help="Chỉ audit Topics 21-33"
    )
    parser.add_argument(
        "--export", "-e", action="store_true", help="Export báo cáo JSON"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Chi tiết từng bài"
    )
    parser.add_argument(
        "--limit", "-l", type=int, default=50, help="Giới hạn số bài audit"
    )

    args = parser.parse_args()

    print("🤖 QUALITY AGENT - Kiểm tra chất lượng nội dung")
    print("=" * 70)

    agent = QualityAgent()

    # Define target articles
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
        # Single article
        article = agent.get_article(args.article_id)
        if article:
            report = agent.audit_article(article)
            agent.print_report(report, verbose=True)
        else:
            print(f"❌ Không tìm thấy article ID {args.article_id}")

    elif args.topics:
        # Topics 21-33 only
        print(f"📋 Audit Topics 21-33 ({len(TOPICS_21_33)} bài)...")
        reports = agent.audit_all(TOPICS_21_33)

        if args.verbose:
            for r in reports:
                agent.print_report(r, verbose=True)

        agent.print_summary(reports)

        if args.export:
            agent.export_report(reports, "quality_topics21-33.json")

    else:
        # All articles (with limit)
        print(f"📋 Audit tất cả articles (limit: {args.limit})...")
        articles = agent.get_all_articles(limit=args.limit)

        reports = []
        for article in articles:
            report = agent.audit_article(article)
            reports.append(report)
            if args.verbose:
                agent.print_report(report, verbose=True)

        agent.print_summary(reports)

        if args.export:
            agent.export_report(reports)


if __name__ == "__main__":
    main()
