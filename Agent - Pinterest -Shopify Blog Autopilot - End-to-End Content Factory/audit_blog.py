import os
import requests
import re
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOP = os.getenv("SHOPIFY_SHOP")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")


def get_all_articles():
    """Get all articles from the Sustainable Living blog"""
    url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json"
    headers = {"X-Shopify-Access-Token": TOKEN}

    all_articles = []
    params = {"limit": 250}

    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Error: {response.status_code}")
            break

        data = response.json()
        articles = data.get("articles", [])
        all_articles.extend(articles)

        # Check for pagination
        link_header = response.headers.get("Link", "")
        if 'rel="next"' in link_header:
            for link in link_header.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<> ")
                    params = {}
                    break
        else:
            break

    return all_articles


def count_images(body_html):
    """Count images in body HTML"""
    if not body_html:
        return 0
    img_pattern = r"<img[^>]+>"
    return len(re.findall(img_pattern, body_html, re.IGNORECASE))


def check_11_sections(body_html):
    """Check if article has proper 11-section structure"""
    if not body_html:
        return False, []

    required_sections = [
        "Direct Answer",
        "Key Conditions",
        "Understanding|Why",
        "Step-by-Step|Guide|How to",
        "Types|Varieties",
        "Troubleshooting",
        "Pro Tips|Expert",
        "FAQ|Frequently Asked",
        "Advanced",
        "Comparison Table|table",
        "Sources|Further Reading",
    ]

    missing = []
    for section in required_sections:
        if not re.search(section, body_html, re.IGNORECASE):
            missing.append(section.split("|")[0])

    return len(missing) == 0, missing


print("=" * 70)
print("COMPREHENSIVE BLOG AUDIT - Sustainable Living Blog")
print("=" * 70)

articles = get_all_articles()
print(f"\nTotal articles: {len(articles)}")

# Categorize issues
low_word_articles = []
no_image_articles = []
few_image_articles = []
missing_sections_articles = []

for article in articles:
    body = article.get("body_html", "") or ""
    word_count = len(body.split())
    image_count = count_images(body)
    has_featured = bool(article.get("image"))
    has_all_sections, missing = check_11_sections(body)

    # Track issues
    if word_count < 500:
        low_word_articles.append(
            {"id": article["id"], "title": article["title"], "word_count": word_count}
        )

    if image_count == 0:
        no_image_articles.append(
            {
                "id": article["id"],
                "title": article["title"],
                "word_count": word_count,
                "has_featured": has_featured,
            }
        )
    elif image_count < 3:
        few_image_articles.append(
            {
                "id": article["id"],
                "title": article["title"],
                "image_count": image_count,
                "has_featured": has_featured,
            }
        )

    if not has_all_sections and word_count >= 500:
        missing_sections_articles.append(
            {
                "id": article["id"],
                "title": article["title"],
                "missing": missing[:3],  # First 3 missing
            }
        )

# Sort results
low_word_articles.sort(key=lambda x: x["word_count"])
no_image_articles.sort(key=lambda x: x["word_count"], reverse=True)
few_image_articles.sort(key=lambda x: x["image_count"])

# Report
print("\n" + "=" * 70)
print(f"≡ƒôè ARTICLES WITH <500 WORDS: {len(low_word_articles)}")
print("=" * 70)
if low_word_articles:
    for a in low_word_articles[:10]:
        print(f"  {a['id']} - {a['title'][:45]:45s} - {a['word_count']} words")
    if len(low_word_articles) > 10:
        print(f"  ... and {len(low_word_articles) - 10} more")
else:
    print("  Γ£à All articles have 500+ words!")

print("\n" + "=" * 70)
print(f"≡ƒû╝∩╕Å ARTICLES WITH NO INLINE IMAGES: {len(no_image_articles)}")
print("=" * 70)
if no_image_articles:
    for a in no_image_articles[:20]:
        featured = "Γ£ô featured" if a["has_featured"] else "Γ£ù no featured"
        print(
            f"  {a['id']} - {a['title'][:40]:40s} - {a['word_count']} words - {featured}"
        )
    if len(no_image_articles) > 20:
        print(f"  ... and {len(no_image_articles) - 20} more")
else:
    print("  Γ£à All articles have inline images!")

print("\n" + "=" * 70)
print(f"≡ƒû╝∩╕Å ARTICLES WITH <3 INLINE IMAGES: {len(few_image_articles)}")
print("=" * 70)
if few_image_articles:
    for a in few_image_articles[:20]:
        featured = "Γ£ô" if a["has_featured"] else "Γ£ù"
        print(
            f"  {a['id']} - {a['title'][:40]:40s} - {a['image_count']} imgs - featured:{featured}"
        )
    if len(few_image_articles) > 20:
        print(f"  ... and {len(few_image_articles) - 20} more")
else:
    print("  Γ£à All articles have 3+ inline images!")

print("\n" + "=" * 70)
print("≡ƒôï SUMMARY")
print("=" * 70)
print(f"  Total articles:           {len(articles)}")
print(f"  Low word count (<500):    {len(low_word_articles)}")
print(f"  No inline images:         {len(no_image_articles)}")
print(f"  Few inline images (<3):   {len(few_image_articles)}")
print(f"  Missing sections:         {len(missing_sections_articles)}")

# Priority list for fixing
print("\n" + "=" * 70)
print("≡ƒÄ» PRIORITY FIX LIST (Good content but no images)")
print("=" * 70)
priority_fix = [a for a in no_image_articles if a["word_count"] >= 1000]
priority_fix.sort(key=lambda x: x["word_count"], reverse=True)
for a in priority_fix[:30]:
    featured = "Γ£ô" if a["has_featured"] else "Γ£ù"
    print(f"  {a['id']} - {a['title'][:45]:45s} - {a['word_count']} words")

print(f"\n  Total priority articles (1000+ words, no images): {len(priority_fix)}")
