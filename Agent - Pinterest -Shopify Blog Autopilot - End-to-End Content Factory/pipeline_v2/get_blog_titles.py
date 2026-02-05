#!/usr/bin/env python3
"""
Get titles of all 65 blogs that need regeneration
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

SHOP = os.getenv("SHOPIFY_SHOP", "the-rike-inc.myshopify.com")
TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
BLOG_ID = os.getenv("SHOPIFY_BLOG_ID", "108441862462")
HEADERS = {"X-Shopify-Access-Token": TOKEN}

# 32 from just_publish + 33 from needs_blockquotes
ids_just_publish = [
    "690523668798",
    "690523406654",
    "690331255102",
    "690331025726",
    "690330829118",
    "690330468670",
    "690330337598",
    "690330272062",
    "690327814462",
    "690327650622",
    "690326241598",
    "690326176062",
    "690325946686",
    "690325389630",
    "690324734270",
    "690323980606",
    "690323947838",
    "690323849534",
    "690315067710",
    "690315034942",
    "690314838334",
    "690314707262",
    "690314641726",
    "690309103934",
    "690308907326",
    "690305466686",
    "690296258878",
    "690295046462",
    "690292425022",
    "690291212606",
    "690283413822",
    "690199724350",
]

ids_needs_blockquotes = [
    "690499551550",
    "690498470206",
    "690497061182",
    "690496241982",
    "690332238142",
    "690332205374",
    "690328338750",
    "690325094718",
    "690323554622",
    "690323489086",
    "690322604350",
    "690322276670",
    "690314871102",
    "690314346814",
    "690313953598",
    "690308645182",
    "690296357182",
    "690211750206",
    "690211717438",
    "690211684670",
    "690211651902",
    "690211127614",
    "690200379710",
    "689588207934",
    "682957963582",
    "682730553662",
    "682692935998",
    "682578575678",
    "682437443902",
    "682428006718",
    "682423877950",
    "682423517502",
    "682423419198",
]

all_ids = ids_just_publish + ids_needs_blockquotes

print(f"Total blogs to regenerate: {len(all_ids)}")
print("=" * 80)

for i, aid in enumerate(all_ids, 1):
    r = requests.get(
        f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{aid}.json",
        headers=HEADERS,
    )
    art = r.json()["article"]
    title = art["title"]
    words = len((art.get("body_html", "") or "").split())
    print(f"{i}. [{aid}] {title} ({words} words)")
