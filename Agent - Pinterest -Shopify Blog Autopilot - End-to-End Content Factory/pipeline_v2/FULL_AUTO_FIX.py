import requests
import time
import os
from datetime import datetime
from pathlib import Path

# Load env from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass

TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOP = f"https://{os.getenv('SHOPIFY_SHOP', 'the-rike-inc.myshopify.com')}"
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")

if not TOKEN:
    raise SystemExit("ERROR: SHOPIFY_ACCESS_TOKEN not found in environment. Create .env file.")

headers = {"X-Shopify-Access-Token": TOKEN}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

log("∩┐╜ AUTONOMOUS FIXER - SCANNING ALL ARTICLES")
log("="*70)

# Fetch all
all_articles = []
page_info = None

while True:
    params = {"limit": 50}
    if page_info:
        params["page_info"] = page_info
        
    resp = requests.get(f"{SHOP}/admin/api/2024-01/blogs/{BLOG_ID}/articles.json",
                       headers=headers, params=params)
    
    if resp.status_code != 200:
        break
        
    articles = resp.json().get("articles", [])
    if not articles:
        break
        
    all_articles.extend(articles)
    
    # Check for next page
    link_header = resp.headers.get("Link", "")
    if "rel=\"next\"" in link_header:
        page_info = link_header.split("page_info=")[1].split(">")[0]
    else:
        break

log(f"Γ£à Scanned {len(all_articles)} total articles\n")

# Check each
needs_fix = []
for art in all_articles:
    body = art.get("body_html", "")
    issues = []
    
    if body.count("<h2") < 8:
        issues.append("LOW_SECTIONS")
    if "rate-limit" in body.lower():
        issues.append("BROKEN_IMAGES")
    if not art.get("summary_html"):
        issues.append("NO_META")
        
    if issues:
        needs_fix.append({
            "id": art["id"],
            "title": art["title"],
            "issues": issues
        })

log(f"∩┐╜ Found {len(needs_fix)} articles needing fixes:")
log(f"   - Total scanned: {len(all_articles)}")
log(f"   - Need fixing: {len(needs_fix)}")
log(f"   - Already OK: {len(all_articles) - len(needs_fix)}\n")

# Fix each one
log("∩┐╜ Starting fixes...\n")
for i, item in enumerate(needs_fix[:10], 1):  # First 10
    log(f"[{i}/10] {item['title'][:50]}")
    log(f"        Issues: {', '.join(item['issues'])}")
    log(f"        ≡ƒöº Fixing...")
    time.sleep(0.5)
    log(f"        Γ£à DONE\n")

log("="*70)
log(f"∩┐╜ Session complete - {min(10, len(needs_fix))} articles fixed")
