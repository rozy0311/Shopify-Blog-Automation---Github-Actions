import os
import requests
import json
import re
from bs4 import BeautifulSoup

GENERIC_PHRASES = [
    "this comprehensive guide provides",
    "this comprehensive guide covers",
    "whether you are a beginner",
    "whether you're a beginner",
    "natural materials vary throughout",
    "professional practitioners recommend",
    "achieving consistent results requires attention",
    "once you've perfected small batches",
    "once you have perfected small batches",
    "scaling up becomes appealing",
    "making larger batches requires",
    "heat distribution",
    "doubling recipes",
    "this practical guide",
    "this guide covers practical",
    "perfect for anyone looking to improve",
    "join thousands who have already mastered",
    "measuring cups",
    "dry ingredients",
    "wet ingredients",
    "shelf life 2-4 weeks",
    "shelf life 3-6 months",
]

SHOP = os.environ.get("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get("SHOPIFY_TOKEN")
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "108441862462")  # Sustainable Living
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")
SCAN_LIMIT = int(os.environ.get("SCAN_LIMIT", "0") or 0)
YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
KEBAB_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

if not TOKEN:
    raise SystemExit("Missing SHOPIFY_ACCESS_TOKEN")

headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# Get ALL published articles and find ones with issues
all_articles = []
all_issues = []

# Paginate through all articles
url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles.json?limit=250&published_status=published"
response = requests.get(url, headers=headers)

if response.status_code == 200:
    articles = response.json().get("articles", [])
    print(f"Found {len(articles)} published articles")

    for art in articles:
        art_id = art.get("id")
        title = art.get("title", "")[:50]
        has_meta = bool(art.get("summary_html"))
        has_image = bool(art.get("image"))
        body = art.get("body_html", "") or ""
        img_count = body.count("<img")
        soup = BeautifulSoup(body, "html.parser")
        text = soup.get_text(" ", strip=True)
        word_count = len(re.findall(r"\w+", text))
        h2_count = len(soup.find_all("h2"))
        links = [
            a for a in soup.find_all("a", href=True) if a["href"].startswith("http")
        ]
        hidden_links = [
            a for a in links if "http" not in a.get_text(" ", strip=True).lower()
        ]
        hidden_link_count = len(hidden_links)
        source_links = [a for a in hidden_links if "—" in a.get_text(" ", strip=True)]
        source_link_count = len(source_links)
        has_broken = (
            "Cdn Shopify" in body
            or "Image Pollinations" in body
            or "rate limit" in body.lower()
        )
        body_lower = body.lower()
        generic_found = [p for p in GENERIC_PHRASES if p in body_lower]
        has_years = bool(YEAR_PATTERN.search(title) or YEAR_PATTERN.search(body))

        # Direct Answer (first paragraph) word count
        first_p = soup.find("p")
        intro_words = 0
        if first_p:
            intro_text = first_p.get_text(" ", strip=True)
            intro_words = len(re.findall(r"\w+", intro_text))

        # Key Terms section
        has_key_terms = bool(
            soup.find("h2", string=re.compile(r"key terms", re.IGNORECASE))
            or soup.find(id=re.compile(r"key-terms", re.IGNORECASE))
        )

        # Sources section and link format
        sources_h2 = None
        for h2 in soup.find_all("h2"):
            if re.search(
                r"sources|further reading|references",
                h2.get_text(" ", strip=True),
                re.IGNORECASE,
            ):
                sources_h2 = h2
                break
        sources_links = []
        if sources_h2:
            for sib in sources_h2.find_next_siblings():
                if sib.name == "h2":
                    break
                sources_links.extend(sib.find_all("a", href=True))
        source_links_text = [a.get_text(" ", strip=True) for a in sources_links]
        links_without_em_dash = [
            t for t in source_links_text if "—" not in t and "–" not in t
        ]
        links_with_raw_url = [
            t
            for t in source_links_text
            if re.search(r"\.(com|org|edu|gov)\b", t, re.IGNORECASE)
        ]

        # Expert quotes check
        blockquotes = soup.find_all("blockquote")
        valid_quotes = 0
        for bq in blockquotes:
            if re.search(
                r"[—–-]\s*(?:Dr\.?\s+)?[A-Z][a-z]+", bq.get_text(" ", strip=True)
            ):
                valid_quotes += 1

        # Stats check
        stat_patterns = [
            r"\d+(?:\.\d+)?%",
            r"\d+(?:,\d{3})+",
            r"\d+(?:\.\d+)?\s*(?:ml|g|oz|lb|kg|cm|inch|hours?|minutes?|days?|weeks?|months?)",
        ]
        stats_found = sum(
            len(re.findall(p, text, re.IGNORECASE)) for p in stat_patterns
        )

        # Heading IDs (kebab-case) check
        headings_without_id = len(
            [h for h in soup.find_all(["h2", "h3"]) if not h.get("id")]
        )
        invalid_heading_ids = [
            h.get("id")
            for h in soup.find_all(["h2", "h3"])
            if h.get("id") and not KEBAB_PATTERN.match(h.get("id"))
        ]

        # External link rel check
        external_links = [
            a for a in links if "the-rike" not in a.get("href", "").lower()
        ]
        links_missing_rel = [
            a
            for a in external_links
            if "rel" not in a.attrs or "nofollow" not in (a.get("rel") or [])
        ]

        # Schema in body
        has_schema = "application/ld+json" in body_lower or '"@context"' in body

        # 11-section structure (approx)
        key_section_patterns = [
            r"direct answer|key conditions|at a glance",
            r"understanding\s+\w+",
            r"step-by-step|complete step",
            r"types and varieties|troubleshooting",
            r"pro tips|expert|blockquote",
            r"faq|frequently asked",
            r"advanced techniques|comparison table",
            r"sources\s*&|further reading|references",
        ]
        sections_found = sum(
            1 for p in key_section_patterns if re.search(p, body_lower, re.IGNORECASE)
        )

        issues = []
        if not has_meta:
            issues.append("NO_META")
        if not has_image:
            issues.append("NO_FEATURED")
        if img_count < 3:
            issues.append(f"LOW_IMGS:{img_count}")
        if has_broken:
            issues.append("BROKEN_TEXT")
        if h2_count < 11:
            issues.append(f"LOW_H2:{h2_count}")
        if word_count < 1800 or word_count > 2500:
            issues.append(f"WORD_COUNT:{word_count}")
        if hidden_link_count < 2:
            issues.append(f"LOW_HIDDEN_LINKS:{hidden_link_count}")
        if source_link_count < 5:
            issues.append(f"LOW_SOURCE_LINKS:{source_link_count}")
        if generic_found:
            issues.append(f"GENERIC:{len(generic_found)}")
        if has_years:
            issues.append("HAS_YEAR")
        if intro_words and (intro_words < 50 or intro_words > 100):
            issues.append(f"DIRECT_ANSWER_WORDS:{intro_words}")
        if not has_key_terms:
            issues.append("MISSING_KEY_TERMS")
        if not sources_h2:
            issues.append("MISSING_SOURCES_SECTION")
        if sources_h2 and len(sources_links) < 5:
            issues.append(f"LOW_SOURCES:{len(sources_links)}")
        if links_without_em_dash:
            issues.append("SOURCE_FORMAT_NO_EM_DASH")
        if links_with_raw_url:
            issues.append("SOURCE_FORMAT_RAW_URL")
        if valid_quotes < 2:
            issues.append(f"LOW_QUOTES:{valid_quotes}")
        if stats_found < 3:
            issues.append(f"LOW_STATS:{stats_found}")
        if headings_without_id > 0:
            issues.append(f"MISSING_HEADING_IDS:{headings_without_id}")
        if invalid_heading_ids:
            issues.append("INVALID_HEADING_IDS")
        if links_missing_rel:
            issues.append("LINKS_MISSING_NOFOLLOW")
        if has_schema:
            issues.append("SCHEMA_IN_BODY")
        if sections_found < 8:
            issues.append(f"LOW_SECTIONS:{sections_found}")

        # TITLE_REPEATS: subtitle duplicates main title ("Topic: Topic...")
        full_title = art.get("title", "")
        for sep in [": ", " : ", " - ", " – ", " — "]:
            if sep in full_title:
                _idx = full_title.index(sep)
                _pa = full_title[:_idx].strip().lower()
                _pb = full_title[_idx + len(sep) :].strip().lower()
                if _pa and _pb:
                    _aw = _pa.split()
                    _bw = _pb.split()
                    if len(_aw) >= 3 and len(_bw) >= 3:
                        _ov = sum(1 for a, b in zip(_aw, _bw) if a == b)
                        if _ov >= 3 and _ov >= len(_bw) * 0.5:
                            issues.append("TITLE_REPEATS")
                            break
                    if len(_pa) >= 20 and _pb.startswith(_pa[:20]):
                        issues.append("TITLE_REPEATS")
                        break
                    if _pa == _pb:
                        issues.append("TITLE_REPEATS")
                        break

        if issues:
            all_issues.append({"id": art_id, "title": title, "issues": issues})

    print(f"\nTotal articles with issues: {len(all_issues)}")
    print("\n--- ARTICLES NEEDING FIX ---")
    for i, item in enumerate(all_issues[:30]):
        print(f'{i+1}. ID:{item["id"]} | {item["title"]} | {item["issues"]}')

    if SCAN_LIMIT > 0:
        all_issues = all_issues[:SCAN_LIMIT]
        print(f"\nScan limit enabled: keeping first {SCAN_LIMIT} items")

    # Save to file for processing
    with open("articles_to_fix.json", "w", encoding="utf-8") as f:
        json.dump(all_issues, f, indent=2)
    print(f"\nSaved {len(all_issues)} articles to articles_to_fix.json")
else:
    print(f"Error: {response.status_code}")
    print(response.text[:500])
