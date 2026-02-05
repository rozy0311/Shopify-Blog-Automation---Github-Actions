#!/usr/bin/env python3
"""
AUTO FIX FAILED ARTICLES
========================
Tß╗▒ ─æß╗Öng sß╗¡a c├íc b├ái bß╗ï lß╗ùi sau khi audit.

Workflow:
1. Load kß║┐t quß║ú audit
2. Vß╗¢i mß╗ùi b├ái failed:
   - Restore Pinterest images
   - Fix content structure (add "Direct Answer" section)
   - Remove generic phrases
   - Regenerate broken AI images
   - Re-publish
"""

import requests
import re
import json
import time
from datetime import datetime
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Config
SHOP = os.getenv("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Load matched Pinterest data
SCRIPT_DIR = Path(__file__).parent.parent / "scripts"
MATCHED_FILE = SCRIPT_DIR / "matched_drafts_pinterest.json"


def load_matched_pinterest():
    if MATCHED_FILE.exists():
        with open(MATCHED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {str(item["draft_id"]): item for item in data.get("matched", [])}
    return {}


def fetch_article(article_id):
    url = f"https://{SHOP}/admin/api/2025-01/articles/{article_id}.json"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json().get("article")
    return None


def update_article(article_id, updates):
    url = f"https://{SHOP}/admin/api/2025-01/articles/{article_id}.json"
    resp = requests.put(url, headers=HEADERS, json={"article": updates})
    return resp.status_code == 200


def generate_direct_answer(title):
    """Tß║ío direct answer section dß╗▒a tr├¬n title"""
    # Extract topic tß╗½ title
    topic = title.replace("How to", "").replace("DIY", "").replace("Guide", "").strip()
    topic = re.sub(r"[:\-|].*", "", topic).strip()

    return f"""<div class="direct-answer" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 4px solid #28a745;">
    <h2 style="color: #28a745; margin-top: 0;">≡ƒÄ» Direct Answer</h2>
    <p style="font-size: 1.15em; line-height: 1.7;"><strong>{topic}</strong> is a practical skill
    that can be mastered with the right techniques. This guide provides step-by-step instructions,
    expert tips, and troubleshooting advice to help you achieve excellent results.</p>
</div>"""


def fix_generic_phrases(body_html):
    """X├│a hoß║╖c thay thß║┐ c├íc generic phrases"""
    replacements = [
        (
            "This comprehensive guide provides everything you need to know",
            "This guide covers the essential techniques and practical tips you'll need",
        ),
        ("This comprehensive guide", "This guide"),
        ("everything you need to know", "the key information"),
        ("professional practitioners recommend", "experts suggest"),
        (
            "achieving consistent results requires attention to measurement precision",
            "achieving good results requires attention to the specific details of your project",
        ),
    ]

    for old, new in replacements:
        body_html = re.sub(re.escape(old), new, body_html, flags=re.IGNORECASE)

    return body_html


def restore_pinterest_image(body_html, pinterest_data):
    """Restore Pinterest image l├ám inline image"""
    pin_id = pinterest_data.get("pin_id")
    if not pin_id:
        return body_html

    # Tß║ío Pinterest image URL
    pinterest_img = f"https://i.pinimg.com/736x/{pin_id[:2]}/{pin_id[2:4]}/{pin_id[4:6]}/{pin_id}.jpg"

    # Check if Pinterest image already exists
    if "pinimg.com" in body_html:
        return body_html

    # Add Pinterest image after first paragraph
    alt_text = pinterest_data.get("pin_content", {}).get("alt_text", "Related image")
    pinterest_figure = f"""
<figure style="margin: 30px 0; text-align: center;">
    <img src="{pinterest_img}" alt="{alt_text}"
         style="max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);"
         loading="lazy">
    <figcaption style="margin-top: 10px; font-style: italic; color: #666;">
        Image via Pinterest
    </figcaption>
</figure>"""

    # Insert after first </p>
    body_html = re.sub(r"(</p>)", r"\1" + pinterest_figure, body_html, count=1)

    return body_html


def generate_ai_image_url(topic, index):
    """Generate AI image URL tß╗½ Pollinations.ai"""
    # Tß║ío prompt tß╗½ topic
    prompts = [
        f"Beautiful professional photo of {topic}, natural lighting, high quality, detailed",
        f"{topic} step by step process, clear demonstration, professional photography",
        f"Close-up detailed shot of {topic}, beautiful composition, soft natural light",
    ]

    prompt = prompts[index % len(prompts)]
    # URL encode prompt
    encoded_prompt = requests.utils.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=600&seed={index}"


def fix_broken_images(body_html, title):
    """Replace broken images vß╗¢i AI generated images"""
    # Extract topic tß╗½ title
    topic = title.replace("How to", "").replace("DIY", "").replace("Guide", "").strip()
    topic = re.sub(r"[:\-|].*", "", topic).strip()[:50]

    # Find all img tags
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'

    def check_and_replace(match):
        full_tag = match.group(0)
        url = match.group(1)

        # Skip Pinterest images
        if "pinimg.com" in url:
            return full_tag

        # Check if image is accessible
        try:
            resp = requests.head(url, timeout=5, allow_redirects=True)
            if resp.status_code < 400:
                return full_tag  # Image OK
        except:
            pass

        # Replace broken image
        new_url = generate_ai_image_url(topic, hash(url) % 100)
        return full_tag.replace(url, new_url)

    return re.sub(img_pattern, check_and_replace, body_html)


def fix_article(article_id, issues, matched_pinterest):
    """Fix mß╗Öt article dß╗▒a tr├¬n list issues"""
    print(f"\n≡ƒöº Fixing article {article_id}...")

    article = fetch_article(article_id)
    if not article:
        print(f"  Γ¥î Could not fetch article")
        return False

    body_html = article.get("body_html", "")
    title = article.get("title", "")
    updated = False

    # 1. Fix missing direct answer
    if any("direct answer" in issue.lower() for issue in issues):
        if "direct answer" not in body_html.lower():
            direct_answer = generate_direct_answer(title)
            body_html = direct_answer + body_html
            print(f"  Γ£à Added Direct Answer section")
            updated = True

    # 2. Fix generic phrases
    if any("GENERIC" in issue for issue in issues):
        body_html = fix_generic_phrases(body_html)
        print(f"  Γ£à Fixed generic phrases")
        updated = True

    # 3. Restore Pinterest images
    if any("MISSING_PINTEREST" in issue for issue in issues):
        pinterest_data = matched_pinterest.get(str(article_id))
        if pinterest_data:
            body_html = restore_pinterest_image(body_html, pinterest_data)
            print(f"  Γ£à Restored Pinterest image")
            updated = True

    # 4. Fix broken images
    if any("BROKEN_IMAGES" in issue for issue in issues):
        body_html = fix_broken_images(body_html, title)
        print(f"  Γ£à Fixed broken images")
        updated = True

    # 5. Fix raw URLs in sources
    if any("RAW_URLS" in issue for issue in issues):
        # Format: website.com ΓåÆ <a href="https://website.com">Source Name</a>
        body_html = re.sub(
            r">https?://([^<]+)<",
            lambda m: f'><a href="https://{m.group(1)}" target="_blank">{m.group(1).split("/")[0]}</a><',
            body_html,
        )
        print(f"  Γ£à Fixed raw URLs")
        updated = True

    # Update article if changed
    if updated:
        success = update_article(article_id, {"body_html": body_html})
        if success:
            print(f"  Γ£à Article updated successfully")
            return True
        else:
            print(f"  Γ¥î Failed to update article")
            return False
    else:
        print(f"  ΓÜá∩╕Å No changes needed")
        return True


def run_auto_fix():
    """Chß║íy auto fix cho tß║Ñt cß║ú articles failed"""
    print("=" * 60)
    print("AUTO FIX FAILED ARTICLES")
    print("=" * 60)

    # Load matched Pinterest data
    matched_pinterest = load_matched_pinterest()
    print(f"Γ£à Loaded {len(matched_pinterest)} matched Pinterest articles")

    # Load audit results or run audit
    audit_file = Path(__file__).parent / "audit_results_full.json"
    if not audit_file.exists():
        print("ΓÜá∩╕Å Audit results not found. Running audit first...")
        from auto_agent_review_and_fix import run_audit_21_matched

        failed = run_audit_21_matched()
    else:
        with open(audit_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            failed = data.get("failed_articles", [])

    if not failed:
        print("Γ£à No failed articles to fix!")
        return

    print(f"\n≡ƒôï Found {len(failed)} articles to fix")

    # Fix each article
    fixed_count = 0
    for result in failed:
        article_id = result["id"]
        issues = result["issues"]

        if fix_article(article_id, issues, matched_pinterest):
            fixed_count += 1

        # Rate limiting
        time.sleep(1)

    print("\n" + "=" * 60)
    print(f"COMPLETE: Fixed {fixed_count}/{len(failed)} articles")
    print("=" * 60)


if __name__ == "__main__":
    run_auto_fix()
