#!/usr/bin/env python3
"""Update all previously published articles to add sources section"""

import requests
import json

SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
API_VERSION = "2025-01"
BLOG_ID = "108441862462"

headers = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}

# All articles to update with their sources
articles_to_update = [
    {
        "id": 690495095102,
        "title": "How to Make Homemade Vinegar from Fruit Scraps",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://www.foodandwine.com/how-to-make-vinegar-at-home-8637498" target="_blank" rel="noopener">Food & Wine - How to Make Vinegar at Home</a></li>
<li><a href="https://www.seriouseats.com/diy-fruit-scrap-vinegar" target="_blank" rel="noopener">Serious Eats - DIY Fruit Scrap Vinegar</a></li>
<li><a href="https://www.masterclass.com/articles/homemade-vinegar" target="_blank" rel="noopener">MasterClass - Homemade Vinegar Guide</a></li>
</ul>""",
    },
    {
        "id": 690495291710,
        "title": "DIY Vanilla Extract at Home",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://www.seriouseats.com/how-to-make-vanilla-extract" target="_blank" rel="noopener">Serious Eats - How to Make Vanilla Extract</a></li>
<li><a href="https://www.foodnetwork.com/how-to/packages/food-network-essentials/how-to-make-vanilla-extract" target="_blank" rel="noopener">Food Network - How to Make Vanilla Extract</a></li>
<li><a href="https://www.thekitchn.com/how-to-make-vanilla-extract-cooking-lessons-from-the-kitchn-185471" target="_blank" rel="noopener">The Kitchn - DIY Vanilla Extract</a></li>
</ul>""",
    },
    {
        "id": 690495324478,
        "title": "Herb-Infused Oils for Cooking and Skincare",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://blog.mountainroseherbs.com/herb-infused-oils" target="_blank" rel="noopener">Mountain Rose Herbs - Herb-Infused Oils</a></li>
<li><a href="https://www.healthline.com/nutrition/herb-infused-oils" target="_blank" rel="noopener">Healthline - Guide to Herb-Infused Oils</a></li>
<li><a href="https://www.foodsafety.gov/food-safety-charts/safe-minimum-internal-temperatures" target="_blank" rel="noopener">FoodSafety.gov - Safe Food Handling</a></li>
</ul>""",
    },
    {
        "id": 690495357246,
        "title": "Homemade Taco Seasoning Blend",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://www.allrecipes.com/recipe/46653/taco-seasoning-i/" target="_blank" rel="noopener">Allrecipes - Taco Seasoning</a></li>
<li><a href="https://www.seriouseats.com/homemade-taco-seasoning" target="_blank" rel="noopener">Serious Eats - Homemade Taco Seasoning</a></li>
<li><a href="https://www.foodnetwork.com/recipes/food-network-kitchen/homemade-taco-seasoning-5765325" target="_blank" rel="noopener">Food Network - Homemade Taco Seasoning</a></li>
</ul>""",
    },
    {
        "id": 690495390014,
        "title": "Easy Granola Recipe with Oats",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://minimalistbaker.com/simple-healthy-granola/" target="_blank" rel="noopener">Minimalist Baker - Simple Healthy Granola</a></li>
<li><a href="https://www.bonappetit.com/recipe/perfect-granola" target="_blank" rel="noopener">Bon Appétit - Perfect Granola</a></li>
<li><a href="https://www.nytimes.com/2015/04/29/dining/granola-recipe.html" target="_blank" rel="noopener">NYT Cooking - The Only Granola Recipe You'll Ever Need</a></li>
</ul>""",
    },
    {
        "id": 690495422782,
        "title": "How to Make Nut Butter at Home",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://minimalistbaker.com/how-to-make-nut-butter/" target="_blank" rel="noopener">Minimalist Baker - How to Make Nut Butter</a></li>
<li><a href="https://www.seriouseats.com/homemade-nut-butters" target="_blank" rel="noopener">Serious Eats - Homemade Nut Butters</a></li>
<li><a href="https://www.healthline.com/nutrition/nut-butters" target="_blank" rel="noopener">Healthline - Guide to Nut Butters</a></li>
</ul>""",
    },
    {
        "id": 690495488318,
        "title": "Quick Pickles vs Fermented Pickles",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://www.seriouseats.com/fermentation-pickling-guide" target="_blank" rel="noopener">Serious Eats - Fermentation and Pickling Guide</a></li>
<li><a href="https://www.masterclass.com/articles/quick-pickles-vs-fermented-pickles" target="_blank" rel="noopener">MasterClass - Quick Pickles vs Fermented Pickles</a></li>
<li><a href="https://nchfp.uga.edu/how/can_06/pickled_products.html" target="_blank" rel="noopener">National Center for Home Food Preservation - Pickled Products</a></li>
</ul>""",
    },
    {
        "id": 690495521086,
        "title": "Herbal Simple Syrups for Drinks and Desserts",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://www.seriouseats.com/how-to-make-simple-syrup" target="_blank" rel="noopener">Serious Eats - How to Make Simple Syrup</a></li>
<li><a href="https://www.thekitchn.com/how-to-make-herb-infused-simple-syrups-228429" target="_blank" rel="noopener">The Kitchn - Herb-Infused Simple Syrups</a></li>
<li><a href="https://blog.mountainroseherbs.com/herbal-simple-syrups" target="_blank" rel="noopener">Mountain Rose Herbs - Herbal Simple Syrups</a></li>
</ul>""",
    },
    {
        "id": 690495553854,
        "title": "Ginger Paste Meal Prep for Easy Weeknight Cooking",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://www.seriouseats.com/ginger-paste-recipe" target="_blank" rel="noopener">Serious Eats - Ginger Paste Recipe</a></li>
<li><a href="https://www.healthline.com/nutrition/ginger-benefits" target="_blank" rel="noopener">Healthline - Health Benefits of Ginger</a></li>
<li><a href="https://www.bonappetit.com/story/how-to-store-ginger" target="_blank" rel="noopener">Bon Appétit - How to Store Ginger</a></li>
</ul>""",
    },
    {
        "id": 690495586622,
        "title": "How to Make Oat Milk That Doesn't Separate",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://minimalistbaker.com/make-oat-milk/" target="_blank" rel="noopener">Minimalist Baker - How to Make Oat Milk</a></li>
<li><a href="https://www.seriouseats.com/oat-milk-recipe" target="_blank" rel="noopener">Serious Eats - Oat Milk Recipe</a></li>
<li><a href="https://www.thekitchn.com/how-to-make-oat-milk-22992928" target="_blank" rel="noopener">The Kitchn - How to Make Oat Milk</a></li>
</ul>""",
    },
    {
        "id": 690495619390,
        "title": "Building Your Herbal Tea Collection from Scratch",
        "sources": """<h2>Sources</h2>
<ul>
<li><a href="https://blog.mountainroseherbs.com/building-herbal-tea-collection" target="_blank" rel="noopener">Mountain Rose Herbs - Building Your Herbal Tea Collection</a></li>
<li><a href="https://chestnutherbs.com/herbal-infusions-and-decoctions-preparing-medicinal-teas/" target="_blank" rel="noopener">Chestnut School of Herbal Medicine - Preparing Medicinal Teas</a></li>
<li><a href="https://www.healthline.com/nutrition/herbal-tea-benefits" target="_blank" rel="noopener">Healthline - Herbal Tea Benefits</a></li>
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
    success_count = 0
    skip_count = 0
    fail_count = 0

    for article_info in articles_to_update:
        article_id = article_info["id"]
        print(f"\n📝 Updating: {article_info['title']} (ID: {article_id})")

        # Get current article
        article = get_article(article_id)
        if not article:
            print(f"   ❌ Could not fetch article")
            fail_count += 1
            continue

        current_body = article.get("body_html", "")

        # Check if sources already exist
        if "<h2>Sources</h2>" in current_body:
            print(f"   ⚠️ Sources already exist, skipping")
            skip_count += 1
            continue

        # Append sources to the end
        new_body = current_body + article_info["sources"]

        # Update article
        if update_article(article_id, new_body):
            print(f"   ✅ Sources added successfully!")
            success_count += 1
        else:
            print(f"   ❌ Failed to update article")
            fail_count += 1

    print(f"\n{'='*50}")
    print(
        f"📊 Summary: {success_count} updated, {skip_count} skipped, {fail_count} failed"
    )


if __name__ == "__main__":
    main()
