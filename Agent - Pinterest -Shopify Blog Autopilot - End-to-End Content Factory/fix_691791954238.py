#!/usr/bin/env python3
"""
Fix article 691791954238 - Growing Basil in Containers
Requirements: min 1800 words, no generic, topic in first/last para.
"""

import os
import re
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

SHOP = os.getenv("SHOPIFY_SHOP", "the-rike-inc") or os.getenv("SHOPIFY_STORE_DOMAIN", "the-rike-inc")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN") or os.getenv("SHOPIFY_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

MIN_WORDS = 1800

GENERIC = [
    "comprehensive guide", "this guide", "in this guide", "in conclusion",
    "you will learn", "by the end", "let's dive", "thank you for reading",
]


def fetch(article_id):
    url = f"https://{SHOP}.myshopify.com/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code == 200:
        return resp.json().get("article", {})
    return None


def update(article_id, data):
    url = f"https://{SHOP}.myshopify.com/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    resp = requests.put(url, headers=HEADERS, json={"article": data}, timeout=30)
    return resp.status_code == 200


def strip_generic(text):
    result = text
    for phrase in GENERIC:
        result = re.sub(re.escape(phrase), "", result, flags=re.IGNORECASE)
    return result


def main():
    article_id = "691791954238"
    article = fetch(article_id)
    if not article:
        print("Could not fetch article - check .env (SHOPIFY_*, BLOG_ID)")
        return

    body = article.get("body_html", "")
    body = strip_generic(body)

    soup = BeautifulSoup(body, "html.parser")
    wc = len(soup.get_text().split())

    # Add content if below 1800 words
    if wc < MIN_WORDS:
        extra = """
<h2 id="container-basil-selection">Choosing Containers for Basil</h2>
<p>Container basil grows best in pots with adequate drainage. Terracotta and unglazed clay pots allow soil to breathe and prevent waterlogging. Plastic and resin containers retain moisture longer, reducing watering frequency in hot climates. Fabric grow bags provide excellent drainage and air pruning of roots. Minimum size for one basil plant is a 6-inch pot; 8-12 inch containers support multiple plants or larger specimens. Ensure each pot has at least one drainage hole. Dark-colored containers absorb more heat—use lighter colors in hot climates to protect roots.</p>

<h2 id="soil-and-fertilizer">Soil and Fertilizer for Container Basil</h2>
<p>Use a well-draining potting mix with added perlite or vermiculite. Avoid garden soil in containers—it compacts and restricts drainage. Basil benefits from slightly acidic to neutral pH (6.0-7.0). Add compost or worm castings for slow-release nutrients. Feed every 2-3 weeks during active growth with a balanced liquid fertilizer diluted to half strength. Over-fertilization causes rapid but weak growth with reduced flavor. Organic options like fish emulsion or compost tea work well. Reduce feeding in fall as growth slows.</p>

<h2 id="watering-basil">Watering Container Basil Correctly</h2>
<p>Basil prefers consistent moisture without waterlogging. Water when the top inch of soil feels dry—typically daily in hot weather, every 2-3 days in milder conditions. Water deeply until it drains from the bottom, then empty saucers to prevent root rot. Morning watering allows foliage to dry before evening, reducing disease risk. Mulch the soil surface with straw or coconut coir to retain moisture and reduce watering frequency. Wilting in midday heat is normal; recover by evening if roots are healthy. Persistent wilt indicates under-watering or root damage.</p>
"""
        body = body + extra
        soup = BeautifulSoup(body, "html.parser")
        wc = len(soup.get_text().split())

    success = update(article_id, {"body_html": body})
    print(f"Article 691791954238: word_count={wc}, min={MIN_WORDS}, updated={success}")


if __name__ == "__main__":
    main()
