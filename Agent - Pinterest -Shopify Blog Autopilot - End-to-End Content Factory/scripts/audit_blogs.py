#!/usr/bin/env python3
"""
Blog Quality Auditor Agent
Kiểm tra tất cả blogs theo tiêu chuẩn META-PROMPT:
1. Title: Keyword-first, clear payoff
2. Hidden links: Có ít nhất 2-3 source links trong body (clickable nhưng URL ẩn)
3. Content structure: H2, lists, actionable steps
4. Image: Có featured image
"""

import requests
import re
from datetime import datetime

SHOP = "the-rike-inc.myshopify.com"
TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"

# Tiêu chuẩn từ META-PROMPT
QUALITY_STANDARDS = {
    "min_links": 2,  # Tối thiểu 2 hidden links
    "min_h2_tags": 2,  # Tối thiểu 2 headings
    "min_word_count": 500,  # Tối thiểu 500 từ
    "required_image": True,  # Phải có image
}


def get_all_articles():
    """Lấy tất cả articles từ blog"""
    url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json"
    headers = {"X-Shopify-Access-Token": TOKEN}
    params = {"limit": 250}

    response = requests.get(url, headers=headers, params=params)
    return response.json().get("articles", [])


def count_hidden_links(body_html):
    """Đếm số lượng hidden links (anchor tags với href)"""
    if not body_html:
        return 0
    # Tìm tất cả thẻ <a> có href attribute
    pattern = r'<a\s+[^>]*href=["\'][^"\']+["\'][^>]*>[^<]+</a>'
    links = re.findall(pattern, body_html, re.IGNORECASE)
    return len(links)


def count_h2_tags(body_html):
    """Đếm số lượng H2 tags"""
    if not body_html:
        return 0
    pattern = r"<h2[^>]*>"
    return len(re.findall(pattern, body_html, re.IGNORECASE))


def count_words(body_html):
    """Đếm số từ trong content"""
    if not body_html:
        return 0
    # Xóa HTML tags
    text = re.sub(r"<[^>]+>", " ", body_html)
    words = text.split()
    return len(words)


def check_title_quality(title):
    """Kiểm tra title có đạt chuẩn keyword-first không"""
    issues = []

    # Không nên bắt đầu bằng số
    if re.match(r"^\d+\.?\s", title):
        issues.append("Title bắt đầu bằng số")

    # Không nên có năm
    if re.search(r"\b202[0-9]\b", title):
        issues.append("Title chứa năm")

    # Nên có dấu : để tách keyword và payoff
    if ":" not in title:
        issues.append("Title không có ':' (keyword: payoff format)")

    return issues


def audit_article(article):
    """Kiểm tra một article theo tất cả tiêu chuẩn"""
    issues = []

    title = article.get("title", "")
    body_html = article.get("body_html", "")
    has_image = article.get("image") is not None

    # 1. Check title
    title_issues = check_title_quality(title)
    issues.extend(title_issues)

    # 2. Check hidden links
    link_count = count_hidden_links(body_html)
    if link_count < QUALITY_STANDARDS["min_links"]:
        issues.append(
            f"Thiếu hidden links ({link_count}/{QUALITY_STANDARDS['min_links']})"
        )

    # 3. Check H2 structure
    h2_count = count_h2_tags(body_html)
    if h2_count < QUALITY_STANDARDS["min_h2_tags"]:
        issues.append(
            f"Thiếu H2 headings ({h2_count}/{QUALITY_STANDARDS['min_h2_tags']})"
        )

    # 4. Check word count
    word_count = count_words(body_html)
    if word_count < QUALITY_STANDARDS["min_word_count"]:
        issues.append(
            f"Content quá ngắn ({word_count}/{QUALITY_STANDARDS['min_word_count']} words)"
        )

    # 5. Check image
    if QUALITY_STANDARDS["required_image"] and not has_image:
        issues.append("Thiếu featured image")

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


def main():
    print("=" * 70)
    print("🔍 BLOG QUALITY AUDITOR - Theo tiêu chuẩn META-PROMPT")
    print("=" * 70)
    print(f"📅 Audit time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    articles = get_all_articles()
    print(f"📊 Tổng số bài: {len(articles)}")
    print()

    # Filter chỉ các bài Topics 21-33 (sustainable living topics)
    target_keywords = [
        "Beeswax",
        "Composting",
        "Indoor Herb",
        "Natural Fabric Dye",
        "Preserved Lemon",
        "Fruit Leather",
        "Seed Saving",
        "Homemade Yogurt",
        "Upcycled Glass",
        "Natural Air Freshener",
        "Fermenting Vegetable",
        "Herbal Salve",
        "Microgreens",
    ]

    passed = []
    failed = []

    for article in articles:
        title = article.get("title", "")

        # Chỉ audit các bài trong target topics
        is_target = any(kw.lower() in title.lower() for kw in target_keywords)
        if not is_target:
            continue

        result = audit_article(article)

        if result["passed"]:
            passed.append(result)
        else:
            failed.append(result)

    # Report FAILED articles
    if failed:
        print("❌ BÀI CẦN SỬA:")
        print("-" * 70)
        for r in failed:
            print(f"\n📄 {r['title'][:60]}...")
            print(f"   ID: {r['id']}")
            print(
                f"   Links: {r['link_count']} | H2s: {r['h2_count']} | Words: {r['word_count']} | Image: {'✓' if r['has_image'] else '✗'}"
            )
            for issue in r["issues"]:
                print(f"   ⚠️  {issue}")

    # Report PASSED articles
    if passed:
        print("\n" + "=" * 70)
        print("✅ BÀI ĐẠT CHUẨN:")
        print("-" * 70)
        for r in passed:
            print(f"✓ {r['title'][:55]}... (Links: {r['link_count']})")

    # Summary
    print("\n" + "=" * 70)
    print("📊 TỔNG KẾT:")
    print(f"   ✅ Đạt chuẩn: {len(passed)}")
    print(f"   ❌ Cần sửa: {len(failed)}")
    print(
        f"   📈 Tỷ lệ pass: {len(passed)/(len(passed)+len(failed))*100:.1f}%"
        if (passed or failed)
        else "   Không có bài nào để audit"
    )
    print("=" * 70)

    # Return failed articles for fixing
    return failed


if __name__ == "__main__":
    failed_articles = main()
