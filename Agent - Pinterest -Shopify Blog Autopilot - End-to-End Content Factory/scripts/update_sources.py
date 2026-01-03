#!/usr/bin/env python3
"""Update recently published articles to add sources section"""

import requests
import json

SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
API_VERSION = "2025-01"
BLOG_ID = "108441862462"

headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}

# Articles to update with their sources
articles_to_update = [
    {
        "id": 690495652158,
        "title": "Calming Herbal Tea Blends for Better Sleep",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://www.sleepfoundation.org/sleep-hygiene/bedtime-routine-for-adults" target="_blank" rel="noopener">Sleep Foundation - Bedtime Routine for Adults</a></li>
<li><a href="https://chestnutherbs.com/herbal-infusions-and-decoctions-preparing-medicinal-teas/" target="_blank" rel="noopener">Chestnut School of Herbal Medicine - Preparing Medicinal Teas</a></li>
<li><a href="https://blog.mountainroseherbs.com/herbal-infusions-and-decoctions" target="_blank" rel="noopener">Mountain Rose Herbs - Herbal Infusions and Decoctions</a></li>
<li><a href="https://danfetea.com/blogs/news/best-herbal-teas-for-sleep" target="_blank" rel="noopener">DanFe Tea - Best Herbal Teas for Sleep</a></li>
</ul>""",
    },
    {
        "id": 690495684926,
        "title": "How to Dry Herbs from Your Garden",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://mamaonthehomestead.com/how-to-air-dry-herbs/" target="_blank" rel="noopener">Mama on the Homestead - How to Air-Dry Herbs</a></li>
<li><a href="https://blog.mountainroseherbs.com/drying-herbs" target="_blank" rel="noopener">Mountain Rose Herbs - Drying Herbs</a></li>
<li><a href="https://underatinroof.com/blog/old-fashioned-preservation-methods-hang-drying-herbs" target="_blank" rel="noopener">Under A Tin Roof - Old-Fashioned Preservation Methods</a></li>
</ul>""",
    },
    {
        "id": 690495717694,
        "title": "Herbal Infusions vs Decoctions: When to Use Each",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://chestnutherbs.com/herbal-infusions-and-decoctions-preparing-medicinal-teas/" target="_blank" rel="noopener">Chestnut School of Herbal Medicine - Herbal Infusions and Decoctions</a></li>
<li><a href="https://www.botanyculture.com/herbal-infusions-decoctions-guide/" target="_blank" rel="noopener">Botany Culture - Herbal Infusions & Decoctions Guide</a></li>
<li><a href="https://blog.mountainroseherbs.com/herbal-infusions-and-decoctions" target="_blank" rel="noopener">Mountain Rose Herbs - Herbal Infusions and Decoctions</a></li>
</ul>""",
    },
]


def get_article(article_id):
    """Get current article content"""
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("article", {})
    return None


def update_article(article_id, body_html):
    """Update article with new body_html"""
    url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    data = {"article": {"id": article_id, "body_html": body_html}}
    response = requests.put(url, headers=headers, json=data)
    return response.status_code == 200


def main():
    for article_info in articles_to_update:
        article_id = article_info["id"]
        print(f"\n📝 Updating: {article_info['title']} (ID: {article_id})")

        # Get current article
        article = get_article(article_id)
        if not article:
            print(f"   ❌ Could not fetch article")
            continue

        current_body = article.get("body_html", "")

        # Check if sources already exist
        if "<h2>Sources</h2>" in current_body:
            print(f"   ⚠️ Sources already exist, skipping")
            continue

        # Append sources to the end
        new_body = current_body + article_info["sources"]

        # Update article
        if update_article(article_id, new_body):
            print(f"   ✅ Sources added successfully!")
        else:
            print(f"   ❌ Failed to update article")


if __name__ == "__main__":
    main()
