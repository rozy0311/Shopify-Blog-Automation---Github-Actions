#!/usr/bin/env python3
"""Check specific article for quality issues"""
import os
import sys
import re
import json
import requests
from pathlib import Path

# Load env
for p in [
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent.parent.parent / ".env",
]:
    if p.exists():
        from dotenv import load_dotenv

        load_dotenv(p)
        print(f"Loaded env from: {p}")
        break

ARTICLE_ID = "682731602238"

store = os.getenv("SHOPIFY_STORE_DOMAIN", "the-rike-inc.myshopify.com").strip()
if not store.startswith("http"):
    store = "https://" + store
token = os.getenv("SHOPIFY_ACCESS_TOKEN")
blog_id = os.getenv("SHOPIFY_BLOG_ID")

print(f"Store: {store}")
print(f"Token: {'***' + token[-4:] if token else 'MISSING'}")
print(f"Blog ID: {blog_id}")

url = f"{store}/admin/api/2025-01/articles/{ARTICLE_ID}.json"
headers = {"X-Shopify-Access-Token": token}

try:
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    article = r.json().get("article", {})
except Exception as e:
    print(f"Error fetching article: {e}")
    sys.exit(1)

print("\n=== ARTICLE INFO ===")
print(f"ID: {article.get('id')}")
print(f"Title: {article.get('title')}")
print(f"Handle: {article.get('handle')}")
print(f"Published: {article.get('published_at')}")

body = article.get("body_html", "") or ""
word_count = len(body.split())
print(f"Word count: {word_count}")

# Check for GENERIC CONTENT
GENERIC_PHRASES = [
    "comprehensive guide",
    "ultimate guide",
    "complete guide",
    "definitive guide",
    "in this guide",
    "this guide",
    "this article",
    "this blog post",
    "whether you're a beginner",
    "whether you are a beginner",
    "whether you are new",
    "in today's world",
    "in today's fast-paced",
    "in our modern world",
    "you will learn",
    "by the end",
    "throughout this article",
    "in this post",
    "we'll explore",
    "let's dive",
    "let's explore",
    "without further ado",
    "in conclusion",
    "to sum up",
    "in summary",
    "to summarize",
    "game-changer",
    "unlock the potential",
    "master the art",
    "elevate your",
    "transform your",
    "empower yourself",
    "unlock the secrets",
    "discover the power",
    "crucial to understand",
    "it's essential",
    "it is essential",
    "it's important",
    "perfect for anyone",
    "one of the best ways",
    "when it comes to",
    "here's everything you need",
    "read on to learn",
    "practical tips",
    # Extra patterns for Key Terms
    "The primary concept discussed here",
    "A critical element that directly impacts",
    "Understanding this helps you make informed",
    "Mastering this technique separates",
    "This foundational knowledge enables you",
    "Knowing this term helps you communicate",
    "Central to",
    "and used throughout the content below",
]

print("\n=== GENERIC CONTENT CHECK ===")
found_generic = []
body_lower = body.lower()
for phrase in GENERIC_PHRASES:
    if phrase.lower() in body_lower:
        found_generic.append(phrase)

if found_generic:
    print(f"🔴 FOUND {len(found_generic)} generic phrases:")
    for p in found_generic[:10]:
        print(f"  - {p}")
else:
    print("✅ No generic phrases found")

# Check for broken images
print("\n=== IMAGE CHECK ===")
if "Too Many Requests" in body:
    print("🔴 Found 'Too Many Requests' - broken image")
if "pollinations.ai/prompt" in body:
    print("🔴 Found pollinations.ai/prompt URL in body")

# Count images
img_pattern = r'<img[^>]+src="([^"]+)"'
images = re.findall(img_pattern, body)
print(f"Images found: {len(images)}")
if images:
    for i, img in enumerate(images[:5]):
        print(f"  {i+1}. {img[:80]}...")

# Check featured image
featured = article.get("image", {})
if featured:
    print(f"Featured image: {featured.get('src', 'N/A')[:80]}")
else:
    print("🔴 No featured image")

# Check for years (should not have)
print("\n=== YEARS CHECK ===")
years = re.findall(r"\b(19|20)\d{2}\b", body)
if years:
    print(f"🔴 Found {len(years)} year references: {set(years)}")
else:
    print("✅ No years found (good)")

# Check H2 sections
print("\n=== STRUCTURE CHECK ===")
h2_matches = re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.IGNORECASE)
print(f"H2 sections: {len(h2_matches)}")
for h in h2_matches[:10]:
    print(f"  - {h[:50]}")

# Check for sources section
if 'id="sources' in body.lower() or ">Sources<" in body or ">Sources &" in body:
    print("✅ Has Sources section")
else:
    print("🟡 Missing Sources section")

# Check for Key Terms section
if 'id="key-terms' in body.lower() or ">Key Terms<" in body:
    print("✅ Has Key Terms section")
else:
    print("🟡 Missing Key Terms section")

print("\n=== FIRST 500 CHARS ===")
print(body[:500])
