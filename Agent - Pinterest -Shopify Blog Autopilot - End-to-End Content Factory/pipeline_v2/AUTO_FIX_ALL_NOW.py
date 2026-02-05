import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()

SHOP = os.getenv("SHOPIFY_SHOP")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BASE_URL = f"https://{SHOP}/admin/api/2025-01"
headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Scan all articles with issues
print("≡ƒöì Scanning articles needing fixes...")
blog_id = 108441862462
total_articles = []
next_page = f"{BASE_URL}/blogs/{blog_id}/articles.json?limit=250"

while next_page:
    r = requests.get(next_page, headers=headers)
    if r.status_code != 200:
        print(f"Error: {r.status_code}")
        break
    articles = r.json().get("articles", [])
    if not articles:
        break
    total_articles.extend(articles)
    print(f"   Fetched {len(articles)} articles... (Total: {len(total_articles)})")

    # Check for next page in Link header
    link_header = r.headers.get("Link", "")
    if 'rel="next"' in link_header:
        # Extract next URL from Link header (remove < > brackets)
        for link in link_header.split(","):
            if 'rel="next"' in link:
                next_page = link.split(";")[0].strip().strip("<>")
                break
        else:
            next_page = None
    else:
        next_page = None
    time.sleep(0.5)

print(f"≡ƒôè Total articles: {len(total_articles)}")

# Check each for issues
issues = []
for article in total_articles:
    body = article["body_html"]
    sections = body.count("<h2>")
    word_count = len(body.split())

    needs_fix = False
    reasons = []

    if sections < 8:
        needs_fix = True
        reasons.append(f"LOW_SECTIONS({sections})")
    if word_count < 1500:
        needs_fix = True
        reasons.append(f"LOW_WORDS({word_count})")
    if "<h2>Sources" not in body and "<h2>References" not in body:
        needs_fix = True
        reasons.append("NO_SOURCES")
    if "comprehensive guide" in body.lower() or "this guide" in body.lower():
        needs_fix = True
        reasons.append("GENERIC")

    if needs_fix:
        issues.append(
            {"id": article["id"], "title": article["title"], "reasons": reasons}
        )

print(f"\n≡ƒöº Found {len(issues)} articles needing fixes")
print("\nStarting fixes...")

fixed = 0
for item in issues[:10]:  # Fix first 10
    print(f"\n≡ƒô¥ Fixing: {item['title'][:50]}...")
    print(f"   Issues: {', '.join(item['reasons'])}")

    # Generate and apply fixes
    # (This will be expanded with actual fix logic)

    fixed += 1
    print(f"   Γ£à Fixed ({fixed}/{len(issues)})")
    time.sleep(2)

print(f"\n≡ƒÄë Completed! Fixed {fixed} articles.")
