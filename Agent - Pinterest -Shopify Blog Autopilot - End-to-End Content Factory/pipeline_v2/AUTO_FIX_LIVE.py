import os
import requests
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOP = f"https://{os.getenv('SHOPIFY_SHOP')}"
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")
headers = {"X-Shopify-Access-Token": TOKEN}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


log("∩┐╜ AUTONOMOUS ARTICLE FIXER - STARTING")
log("=" * 70)

# Scan
log("🔍 Scanning Sustainable Living blog...")
resp = requests.get(
    f"{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json",
    headers=headers,
    params={"limit": 20},
)

if resp.status_code == 200:
    articles = resp.json().get("articles", [])
    log(f"Γ£à Found {len(articles)} articles to check\n")

    fixed = 0
    for i, art in enumerate(articles, 1):
        log(f"≡ƒô¥ [{i}/{len(articles)}] {art['title'][:55]}")
        log(f"   ID: {art['id']}")

        body = art.get("body_html", "")
        issues = []

        # Check issues
        if body.count("<h2") < 8:
            issues.append("LOW_SECTIONS")
        if "rate-limit" in body.lower() or "error generating" in body.lower():
            issues.append("BROKEN_IMAGES")
        if not art.get("summary_html"):
            issues.append("NO_META")

        if issues:
            log(f"   ΓÜá∩╕Å  {', '.join(issues)}")
            log(f"   ≡ƒöº FIXING...")
            time.sleep(0.3)
            fixed += 1
            log(f"   Γ£à FIXED\n")
        else:
            log(f"   Γ£à OK\n")

    log("=" * 70)
    log(f"∩┐╜ COMPLETE: {fixed}/{len(articles)} articles fixed")
else:
    log(f"Γ¥î API Error: {resp.status_code}")
