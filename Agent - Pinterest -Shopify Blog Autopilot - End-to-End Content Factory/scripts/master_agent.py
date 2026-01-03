#!/usr/bin/env python3
"""
MASTER AGENT - Tự động thực hiện tất cả tasks theo memory
Đọc config từ agent_memory.yaml và tự động:
1. Audit tất cả blogs
2. Fix titles không đạt chuẩn
3. Fix missing images
4. Report kết quả

Chạy: python master_agent.py
"""

import os
import sys
import yaml
import requests
import re
import time
from datetime import datetime

# Load config từ memory
CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "agent_memory.yaml"
)


def load_memory():
    """Load agent memory từ YAML config"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def log(msg, level="INFO"):
    """Print log với timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    symbols = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "ERROR": "❌",
        "WARNING": "⚠️",
        "ACTION": "🔧",
    }
    print(f"[{timestamp}] {symbols.get(level, '•')} {msg}")


class BlogAgent:
    def __init__(self):
        self.memory = load_memory()
        self.shopify = self.memory["shopify"]
        self.pexels = self.memory["pexels"]
        self.standards = self.memory["article_standards"]
        self.topics = self.memory["target_topics"]

        self.base_url = (
            f"https://{self.shopify['shop']}/admin/api/{self.shopify['api_version']}"
        )
        self.headers = {"X-Shopify-Access-Token": self.shopify["token"]}

        self.results = {"passed": [], "failed": [], "fixed": []}

    def get_all_articles(self):
        """Lấy tất cả articles từ Shopify"""
        url = f"{self.base_url}/blogs/{self.shopify['blog_id']}/articles.json"
        response = requests.get(url, headers=self.headers, params={"limit": 250})
        return response.json().get("articles", [])

    def is_target_article(self, title):
        """Kiểm tra article có thuộc target topics không"""
        for topic in self.topics:
            if topic["keyword"].lower() in title.lower():
                return topic
        return None

    def count_hidden_links(self, body_html):
        """Đếm số hidden links trong content"""
        if not body_html:
            return 0
        pattern = r'<a\s+[^>]*href=["\'][^"\']+["\'][^>]*>[^<]+</a>'
        return len(re.findall(pattern, body_html, re.IGNORECASE))

    def count_h2_tags(self, body_html):
        """Đếm số H2 tags"""
        if not body_html:
            return 0
        return len(re.findall(r"<h2[^>]*>", body_html, re.IGNORECASE))

    def count_words(self, body_html):
        """Đếm số từ"""
        if not body_html:
            return 0
        text = re.sub(r"<[^>]+>", " ", body_html)
        return len(text.split())

    def check_title_format(self, title):
        """Kiểm tra title có đúng format không"""
        issues = []
        if re.match(r"^\d+\.?\s", title):
            issues.append("Bắt đầu bằng số")
        if re.search(r"\b202[0-9]\b", title):
            issues.append("Chứa năm")
        if ":" not in title:
            issues.append("Thiếu ':' (keyword: payoff)")
        return issues

    def audit_article(self, article):
        """Audit một article theo tất cả tiêu chuẩn"""
        issues = []
        title = article.get("title", "")
        body = article.get("body_html", "")
        has_image = article.get("image") is not None

        # Check title
        title_issues = self.check_title_format(title)
        issues.extend([f"Title: {i}" for i in title_issues])

        # Check links
        link_count = self.count_hidden_links(body)
        min_links = self.standards["hidden_links"]["min_count"]
        if link_count < min_links:
            issues.append(f"Links: {link_count}/{min_links}")

        # Check H2
        h2_count = self.count_h2_tags(body)
        min_h2 = self.standards["structure"]["min_h2_count"]
        if h2_count < min_h2:
            issues.append(f"H2: {h2_count}/{min_h2}")

        # Check words
        word_count = self.count_words(body)
        min_words = self.standards["structure"]["min_word_count"]
        if word_count < min_words:
            issues.append(f"Words: {word_count}/{min_words}")

        # Check image
        if self.standards["image"]["required"] and not has_image:
            issues.append("Thiếu image")

        return {
            "id": article["id"],
            "title": title,
            "handle": article.get("handle", ""),
            "link_count": link_count,
            "h2_count": h2_count,
            "word_count": word_count,
            "has_image": has_image,
            "issues": issues,
            "passed": len(issues) == 0,
        }

    def get_pexels_image(self, query):
        """Lấy ảnh từ Pexels API"""
        url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": self.pexels["api_key"]}
        params = {"query": query, "per_page": 1, "orientation": "landscape"}

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("photos"):
                photo = data["photos"][0]
                return {
                    "src": photo["src"]["large2x"],
                    "alt": f"{query} - Photo from Pexels",
                }
        return None

    def fix_missing_image(self, article_id, topic):
        """Thêm image cho article thiếu ảnh"""
        image_data = self.get_pexels_image(topic["pexels_query"])
        if not image_data:
            return False

        url = f"{self.base_url}/blogs/{self.shopify['blog_id']}/articles/{article_id}.json"
        headers = {**self.headers, "Content-Type": "application/json"}

        payload = {
            "article": {
                "id": article_id,
                "image": {"src": image_data["src"], "alt": image_data["alt"]},
            }
        }

        response = requests.put(url, headers=headers, json=payload)
        return response.status_code == 200

    def run_audit(self):
        """Chạy audit tất cả target articles"""
        log("Bắt đầu AUDIT tất cả blogs...", "ACTION")

        articles = self.get_all_articles()
        log(f"Tìm thấy {len(articles)} articles tổng cộng")

        for article in articles:
            title = article.get("title", "")
            topic = self.is_target_article(title)

            if not topic:
                continue

            result = self.audit_article(article)
            result["topic"] = topic

            if result["passed"]:
                self.results["passed"].append(result)
            else:
                self.results["failed"].append(result)

        log(
            f"Audit hoàn tất: {len(self.results['passed'])} PASS, {len(self.results['failed'])} FAIL",
            "INFO",
        )

    def run_fixes(self):
        """Tự động fix các issues có thể fix được"""
        log("Bắt đầu AUTO-FIX...", "ACTION")

        for item in self.results["failed"]:
            fixed_issues = []

            # Fix missing image
            if not item["has_image"]:
                log(f"Fixing image: {item['title'][:40]}...", "ACTION")
                if self.fix_missing_image(item["id"], item["topic"]):
                    fixed_issues.append("Added image")
                    log("Image added!", "SUCCESS")
                else:
                    log("Failed to add image", "ERROR")
                time.sleep(0.5)  # Rate limiting

            if fixed_issues:
                self.results["fixed"].append(
                    {"title": item["title"], "fixes": fixed_issues}
                )

    def print_report(self):
        """In báo cáo tổng kết"""
        print("\n" + "=" * 70)
        print("📊 MASTER AGENT REPORT")
        print("=" * 70)
        print(f"📅 Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Failed articles
        if self.results["failed"]:
            print("❌ BÀI CẦN XỬ LÝ THỦ CÔNG (thiếu hidden links):")
            print("-" * 70)
            for r in self.results["failed"]:
                # Only show if still has link issues after fixes
                link_issue = any("Links:" in i for i in r["issues"])
                if link_issue:
                    print(f"  • {r['title'][:55]}...")
                    print(f"    ID: {r['id']} | Links: {r['link_count']}")

        # Passed articles
        if self.results["passed"]:
            print("\n✅ BÀI ĐẠT CHUẨN:")
            print("-" * 70)
            for r in self.results["passed"]:
                print(f"  ✓ {r['title'][:55]}...")

        # Fixed articles
        if self.results["fixed"]:
            print("\n🔧 ĐÃ TỰ ĐỘNG SỬA:")
            print("-" * 70)
            for r in self.results["fixed"]:
                print(f"  • {r['title'][:50]}... → {', '.join(r['fixes'])}")

        # Summary
        print("\n" + "=" * 70)
        print("📈 TỔNG KẾT:")
        total = len(self.results["passed"]) + len(self.results["failed"])
        print(f"   ✅ Đạt chuẩn: {len(self.results['passed'])}")
        print(f"   ❌ Cần sửa: {len(self.results['failed'])}")
        print(f"   🔧 Đã auto-fix: {len(self.results['fixed'])}")
        if total > 0:
            print(f"   📊 Tỷ lệ pass: {len(self.results['passed'])/total*100:.1f}%")
        print("=" * 70)

        # Reminder về những gì cần làm thủ công
        link_issues = [r for r in self.results["failed"] if r["link_count"] < 2]
        if link_issues:
            print(
                "\n💡 LƯU Ý: Các bài thiếu hidden links cần republish thủ công với content mới."
            )
            print("   Chạy: python republish_topic{N}.py cho từng bài")


def main():
    print("=" * 70)
    print("🤖 MASTER BLOG AGENT")
    print("   Đọc yêu cầu từ: config/agent_memory.yaml")
    print("=" * 70)
    print()

    agent = BlogAgent()

    # Step 1: Audit
    agent.run_audit()

    # Step 2: Auto-fix what we can
    agent.run_fixes()

    # Step 3: Report
    agent.print_report()


if __name__ == "__main__":
    main()
