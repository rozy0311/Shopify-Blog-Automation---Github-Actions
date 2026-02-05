#!/usr/bin/env python3
"""Audit one article and write report to file."""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()
SHOP = os.getenv("SHOPIFY_SHOP", "the-rike-inc")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")

def fetch(article_id):
    url = f"https://{SHOP}.myshopify.com/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    resp = requests.get(url, headers={"X-Shopify-Access-Token": TOKEN}, timeout=30)
    if resp.status_code == 200:
        return resp.json().get("article", {})
    return None

GENERIC_PHRASES = [
    "comprehensive guide", "this guide", "in this guide", "in conclusion",
    "you will learn", "by the end", "let's dive", "thank you for reading",
]

def main():
    aid = sys.argv[1] if len(sys.argv) > 1 else "691791954238"
    article = fetch(aid)
    if not article:
        report = {"error": "Could not fetch article"}
    else:
        body = article.get("body_html", "")
        title = article.get("title", "")
        soup = BeautifulSoup(body, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        words = len(text.split())
        images = soup.find_all("img")
        pinterest = [i for i in images if "pinimg.com" in i.get("src", "")]
        tables = soup.find_all("table")
        blockquotes = soup.find_all("blockquote")
        sources = [a for a in soup.find_all("a", href=True) if "http" in a.get("href", "") and "the-rike" not in a.get("href", "")]
        found_generic = [p for p in GENERIC_PHRASES if p in text.lower()]
        paragraphs = soup.find_all("p")
        first_p = paragraphs[0].get_text().lower() if paragraphs else ""
        last_p = paragraphs[-1].get_text().lower() if paragraphs else ""
        topic_kw = [w for w in title.lower().split() if len(w) >= 4 and w not in ("this", "that", "with", "from", "your", "guide")]
        topic_first = any(k in first_p for k in topic_kw[:3])
        topic_last = any(k in last_p for k in topic_kw[:3])
        
        report = {
            "article_id": aid,
            "title": title,
            "word_count": words,
            "min_words": 1600,
            "words_ok": words >= 1600,
            "images": len(images),
            "images_min": 3,
            "images_ok": len(images) >= 3,
            "pinterest_images": len(pinterest),
            "tables": len(tables),
            "blockquotes": len(blockquotes),
            "sources": len(sources),
            "generic_found": found_generic,
            "topic_in_first": topic_first,
            "topic_in_last": topic_last,
            "meta_description": bool(article.get("metafields_global_description_tag") or article.get("summary_html")),
        }
        report["issues"] = []
        if words < 1600:
            report["issues"].append(f"word_count_{words}_below_1600")
        if len(images) < 3:
            report["issues"].append(f"images_{len(images)}_below_3")
        if len(pinterest) < 1:
            report["issues"].append("no_pinterest_image")
        if found_generic:
            report["issues"].append(f"generic_{','.join(found_generic)}")
        if not topic_last:
            report["issues"].append("topic_drift_last_para")
    
    out = Path(__file__).parent / "audit_result.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Written to", str(out))

if __name__ == "__main__":
    main()
