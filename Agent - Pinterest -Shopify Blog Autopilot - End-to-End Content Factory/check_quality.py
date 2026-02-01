#!/usr/bin/env python3
"""Quick quality check for published articles."""

import os
import re
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

SHOP = os.getenv("SHOPIFY_SHOP", "the-rike-inc")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")

# Generic phrases to check
GENERIC_PHRASES = [
    "comprehensive guide", "in this guide", "this guide",
    "in today's world", "in today's fast-paced",
    "you will learn", "by the end", "throughout this article",
    "we'll explore", "let's dive", "let's explore",
    "in conclusion", "to sum up", "in summary",
    "thank you for reading", "happy growing", "happy gardening",
    "whether you're a beginner", "whether you are new",
    "game-changer", "unlock the potential", "master the art",
    "elevate your", "transform your", "empower yourself",
    "crucial to understand", "it's essential", "it is essential",
]

def fetch_article(article_id):
    """Fetch article from Shopify."""
    url = f"https://{SHOP}.myshopify.com/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    headers = {"X-Shopify-Access-Token": TOKEN}
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 200:
        return resp.json().get("article", {})
    print(f"Error fetching article {article_id}: {resp.status_code}")
    return None

def analyze_article(article):
    """Analyze article quality."""
    title = article.get("title", "")
    body = article.get("body_html", "")
    meta = article.get("metafields_global_description_tag", "") or article.get("summary_html", "")
    
    soup = BeautifulSoup(body, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    
    # Word count
    words = len(text.split())
    
    # Section headings
    h2s = soup.find_all("h2")
    h3s = soup.find_all("h3")
    
    # Images
    images = soup.find_all("img")
    pinterest_images = [img for img in images if "pinimg.com" in img.get("src", "")]
    
    # Tables
    tables = soup.find_all("table")
    
    # Blockquotes
    blockquotes = soup.find_all("blockquote")
    
    # Sources/citations
    sources = soup.find_all("a", href=True)
    external_sources = [a for a in sources if "http" in a.get("href", "") and SHOP not in a.get("href", "")]
    
    # Check generic phrases
    text_lower = text.lower()
    found_generic = []
    for phrase in GENERIC_PHRASES:
        if phrase.lower() in text_lower:
            found_generic.append(phrase)
    
    # Extract topic keywords from title
    topic_keywords = [w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', title) 
                      if w.lower() not in ("this", "that", "with", "from", "your", "guide", "comprehensive")]
    
    # Check topic drift (first and last paragraphs should mention topic)
    paragraphs = soup.find_all("p")
    first_para = paragraphs[0].get_text().lower() if paragraphs else ""
    last_para = paragraphs[-1].get_text().lower() if paragraphs else ""
    
    topic_in_first = any(kw in first_para for kw in topic_keywords[:3])
    topic_in_last = any(kw in last_para for kw in topic_keywords[:3])
    
    # 11-section structure check
    required_sections = [
        "direct answer", "key conditions", "understanding", "step-by-step",
        "types", "troubleshooting", "pro tips", "faq", "advanced",
        "comparison", "sources"
    ]
    headings_text = " ".join([h.get_text().lower() for h in h2s + h3s])
    sections_found = sum(1 for s in required_sections if s in headings_text)
    
    return {
        "title": title,
        "words": words,
        "h2_count": len(h2s),
        "h3_count": len(h3s),
        "images": len(images),
        "pinterest_images": len(pinterest_images),
        "tables": len(tables),
        "blockquotes": len(blockquotes),
        "external_sources": len(external_sources),
        "generic_phrases": found_generic,
        "topic_keywords": topic_keywords[:5],
        "topic_in_first_para": topic_in_first,
        "topic_in_last_para": topic_in_last,
        "sections_found": sections_found,
        "has_meta": bool(meta and len(meta) > 50),
    }

def print_report(article_id, analysis):
    """Print quality report."""
    print("\n" + "="*70)
    print(f"QUALITY CHECK: {article_id}")
    print(f"Title: {analysis['title']}")
    print("="*70)
    
    # Word count check
    word_status = "[OK]" if 1600 <= analysis['words'] <= 2500 else "[FAIL]"
    print(f"\n{word_status} Words: {analysis['words']} (need 1600-2500)")
    
    # Structure check
    section_status = "[OK]" if analysis['sections_found'] >= 8 else "[FAIL]"
    print(f"{section_status} Sections found: {analysis['sections_found']}/11")
    
    # Images check
    img_status = "[OK]" if analysis['images'] >= 3 else "[FAIL]"
    print(f"{img_status} Images: {analysis['images']} (need 3+)")
    
    pinterest_status = "[OK]" if analysis['pinterest_images'] >= 1 else "[WARN]"
    print(f"{pinterest_status} Pinterest images: {analysis['pinterest_images']}")
    
    # Tables check
    table_status = "[OK]" if analysis['tables'] >= 1 else "[FAIL]"
    print(f"{table_status} Tables: {analysis['tables']} (need 1+)")
    
    # Blockquotes check
    quote_status = "[OK]" if analysis['blockquotes'] >= 2 else "[FAIL]"
    print(f"{quote_status} Blockquotes: {analysis['blockquotes']} (need 2+)")
    
    # Sources check
    source_status = "[OK]" if analysis['external_sources'] >= 5 else "[FAIL]"
    print(f"{source_status} External sources: {analysis['external_sources']} (need 5+)")
    
    # Meta description
    meta_status = "[OK]" if analysis['has_meta'] else "[FAIL]"
    print(f"{meta_status} Meta description: {'Yes' if analysis['has_meta'] else 'No'}")
    
    # Generic phrases
    if analysis['generic_phrases']:
        print(f"\n[FAIL] GENERIC PHRASES FOUND ({len(analysis['generic_phrases'])}):")
        for phrase in analysis['generic_phrases'][:10]:
            print(f"   - \"{phrase}\"")
    else:
        print("\n[OK] No generic phrases found")
    
    # Topic drift
    print(f"\nTopic keywords: {', '.join(analysis['topic_keywords'])}")
    drift_first = "[OK]" if analysis['topic_in_first_para'] else "[WARN]"
    drift_last = "[OK]" if analysis['topic_in_last_para'] else "[WARN]"
    print(f"{drift_first} Topic in first paragraph: {analysis['topic_in_first_para']}")
    print(f"{drift_last} Topic in last paragraph: {analysis['topic_in_last_para']}")
    
    # Summary
    issues = []
    if analysis['words'] < 1600:
        issues.append(f"Too short ({analysis['words']} words)")
    if analysis['words'] > 2500:
        issues.append(f"Too long ({analysis['words']} words)")
    if analysis['generic_phrases']:
        issues.append(f"Generic content ({len(analysis['generic_phrases'])} phrases)")
    if not analysis['topic_in_first_para'] or not analysis['topic_in_last_para']:
        issues.append("Possible topic drift")
    if analysis['sections_found'] < 8:
        issues.append(f"Missing sections ({analysis['sections_found']}/11)")
    if analysis['tables'] < 1:
        issues.append("No comparison table")
    if analysis['blockquotes'] < 2:
        issues.append("Insufficient expert quotes")
    if analysis['external_sources'] < 5:
        issues.append("Insufficient sources")
    
    print("\n" + "-"*70)
    if issues:
        print("[FAIL] ISSUES FOUND:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("[OK] ARTICLE MEETS META PROMPT REQUIREMENTS")
    print("-"*70)
    
    return len(issues) == 0

if __name__ == "__main__":
    import sys
    
    # Check articles
    article_ids = sys.argv[1:] if len(sys.argv) > 1 else ["691791954238", "690495586622"]
    
    results = []
    for aid in article_ids:
        article = fetch_article(aid)
        if article:
            analysis = analyze_article(article)
            passed = print_report(aid, analysis)
            results.append((aid, passed))
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    for aid, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {aid}")
