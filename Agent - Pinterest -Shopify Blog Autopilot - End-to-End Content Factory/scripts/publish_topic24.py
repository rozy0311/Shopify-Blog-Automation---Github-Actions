#!/usr/bin/env python3
"""
publish_topic24.py - Publish Topic 24: DIY Beeswax Wraps for Food Storage
"""

import requests
import re

SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
API_VERSION = "2025-01"
BLOG_ID = "108441862462"
AUTHOR = "The Rike"

TOPIC = {
    "id": 24,
    "title": "DIY Beeswax Wraps for Food Storage",
    "seo_title": "DIY Beeswax Wraps for Food Storage | Reusable Wrap Tutorial",
    "seo_desc": "Make your own beeswax wraps to replace plastic wrap! Easy DIY tutorial for reusable, eco-friendly food storage wraps that last for years.",
    "tags": [
        "beeswax wraps",
        "zero waste kitchen",
        "plastic free",
        "DIY food storage",
        "sustainable living",
    ],
}

IMAGES = [
    {
        "url": "https://images.pexels.com/photos/4397840/pexels-photo-4397840.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Colorful beeswax wraps covering food containers as plastic alternative",
    },
    {
        "url": "https://images.pexels.com/photos/4033324/pexels-photo-4033324.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Fresh vegetables wrapped in eco-friendly beeswax food wraps",
    },
    {
        "url": "https://images.pexels.com/photos/5137693/pexels-photo-5137693.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Natural beeswax and fabric materials for making wraps",
    },
    {
        "url": "https://images.pexels.com/photos/4505173/pexels-photo-4505173.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Kitchen counter with sustainable food storage solutions",
    },
]

BODY_HTML = """
<p>Every time you tear off a piece of plastic wrap, you're adding to a problem that persists for centuries. According to the <a href="https://www.epa.gov/" target="_blank" rel="noopener">U.S. Environmental Protection Agency (EPA)</a>, Americans generate nearly <strong>9 billion pounds of plastic film, bags, and wraps annually</strong>. But there's a beautiful, sustainable alternative that's been around for generations: beeswax wraps. And the best part? You can make them yourself in under an hour.</p>

<p>Beeswax wraps are reusable, biodegradable, and naturally antimicrobial—keeping your food fresher, longer, without any of the chemicals found in conventional plastic wrap. Let's dive into how to make your own.</p>

<figure><img src="https://images.pexels.com/photos/4033324/pexels-photo-4033324.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Fresh vegetables wrapped in eco-friendly beeswax food wraps" loading="lazy" /><figcaption>Photo via Pexels</figcaption></figure>

<h2>Why Switch from Plastic to Beeswax Wraps?</h2>

<p>The case against plastic wrap is compelling. As explained by the <a href="https://southernsustainabilityinstitute.org/beeswax-food-wraps-the-eco-friendly-alternative-to-plastic-wrap/" target="_blank" rel="noopener">Southern Sustainability Institute</a>: "Plastic wrap is made from petroleum-based materials, and like other plastics, it is non-biodegradable. This means it can persist in the environment for hundreds of years, polluting oceans, harming wildlife, and ultimately contaminating our ecosystems."</p>

<p>Compare that to beeswax wraps:</p>

<table style="width:100%; border-collapse: collapse; margin: 1rem 0;">
<tr style="background-color: #f8f8f8;">
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Feature</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Plastic Wrap</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Beeswax Wrap</th>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Lifespan</td>
<td style="padding: 12px; border: 1px solid #ddd;">Single use</td>
<td style="padding: 12px; border: 1px solid #ddd;">Up to 1 year or more</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;">Decomposition</td>
<td style="padding: 12px; border: 1px solid #ddd;">Hundreds of years</td>
<td style="padding: 12px; border: 1px solid #ddd;">Fully compostable</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Materials</td>
<td style="padding: 12px; border: 1px solid #ddd;">Petroleum-based</td>
<td style="padding: 12px; border: 1px solid #ddd;">Natural, renewable</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;">Chemical Safety</td>
<td style="padding: 12px; border: 1px solid #ddd;">May contain phthalates, BPA</td>
<td style="padding: 12px; border: 1px solid #ddd;">Chemical-free, food-safe</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Food Freshness</td>
<td style="padding: 12px; border: 1px solid #ddd;">Suffocates food</td>
<td style="padding: 12px; border: 1px solid #ddd;">Breathable, antimicrobial</td>
</tr>
</table>

<h2>What You'll Need</h2>

<p>As <a href="https://homesteadandchill.com/diy-homemade-beeswax-wraps/" target="_blank" rel="noopener">Homestead and Chill</a> notes, you can make beeswax wraps "using only fabric and beeswax" for the most simple method. Here's your complete supply list:</p>

<h3>Essential Materials:</h3>

<ul>
<li><strong>100% cotton fabric</strong> – Organic cotton is ideal, but any natural fiber works</li>
<li><strong>Beeswax</strong> – Pellets or grated from a block (about 1 oz per 12x12" wrap)</li>
<li><strong>Optional: Pine resin</strong> – Adds tackiness and durability</li>
<li><strong>Optional: Jojoba oil</strong> – Adds flexibility and antimicrobial properties</li>
</ul>

<h3>Equipment:</h3>

<ul>
<li>Pinking shears or fabric scissors</li>
<li>Baking sheet lined with parchment paper</li>
<li>Oven or iron</li>
<li>Old paintbrush (for spreading wax)</li>
<li>Newspaper or drop cloth</li>
</ul>

<figure><img src="https://images.pexels.com/photos/5137693/pexels-photo-5137693.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Natural beeswax and fabric materials for making wraps" loading="lazy" /><figcaption>Photo via Pexels</figcaption></figure>

<h2>Step-by-Step Tutorial: Oven Method</h2>

<p>This is the most straightforward method for beginners.</p>

<h3>Step 1: Cut Your Fabric</h3>

<p>Using pinking shears (which prevent fraying), cut your cotton fabric into desired sizes. Recommended sizes:</p>

<ul>
<li><strong>Small (7x8")</strong> – Perfect for covering small bowls or half an avocado</li>
<li><strong>Medium (10x11")</strong> – Ideal for sandwiches and cheese</li>
<li><strong>Large (13x14")</strong> – Great for covering large bowls or wrapping bread</li>
</ul>

<h3>Step 2: Preheat and Prepare</h3>

<p>Preheat your oven to 200°F (93°C). Line a baking sheet with parchment paper and lay your fabric flat on top.</p>

<h3>Step 3: Add the Wax</h3>

<p>Sprinkle beeswax pellets evenly over the fabric. For better performance, use this ratio:</p>

<ul>
<li><strong>4 parts beeswax</strong></li>
<li><strong>1 part pine resin</strong> (optional)</li>
<li><strong>1 part jojoba oil</strong> (optional)</li>
</ul>

<p>If using the simple method, use only beeswax—about 1 tablespoon per 10x10" square.</p>

<h3>Step 4: Melt the Wax</h3>

<p>Place the baking sheet in the oven for 3-4 minutes until the wax melts completely. Watch carefully to avoid overheating.</p>

<h3>Step 5: Spread Evenly</h3>

<p>Remove from oven and immediately use an old paintbrush to spread the wax evenly across the entire fabric. Make sure edges are covered. If any spots look dry, add more wax and return to oven briefly.</p>

<h3>Step 6: Cool and Cure</h3>

<p>Lift the fabric by the edges (it cools quickly) and wave it in the air for 10-20 seconds until the wax sets. Hang to finish cooling or lay flat on a clean surface.</p>

<h2>Alternative Method: Iron</h2>

<p>If you don't want to use your oven:</p>

<ol>
<li>Sandwich the fabric between two sheets of parchment paper</li>
<li>Sprinkle wax on top of the fabric</li>
<li>Iron on medium heat until wax melts through</li>
<li>Peel away while warm and allow to cool</li>
</ol>

<p>This method works well for smaller batches or touch-ups.</p>

<figure><img src="https://images.pexels.com/photos/4505173/pexels-photo-4505173.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Kitchen counter with sustainable food storage solutions" loading="lazy" /><figcaption>Photo via Pexels</figcaption></figure>

<h2>How to Use Your Beeswax Wraps</h2>

<p>The <a href="https://southernsustainabilityinstitute.org/beeswax-food-wraps-the-eco-friendly-alternative-to-plastic-wrap/" target="_blank" rel="noopener">Southern Sustainability Institute</a> explains the science: "Beeswax wraps work by utilizing the natural adhesive properties of beeswax, which gives them their malleability and stickiness when pressed against food."</p>

<p>Here's the technique:</p>

<ol>
<li><strong>Wrap</strong> – Place the beeswax wrap over your food or container</li>
<li><strong>Mold</strong> – Press gently with your hands to shape it. The warmth of your hands softens the wax, allowing you to create a tight seal</li>
<li><strong>Store</strong> – Store food as normal—in the fridge, pantry, or on the countertop</li>
<li><strong>Clean</strong> – Wash with cool water and mild soap, air dry</li>
</ol>

<h2>Best Uses for Beeswax Wraps</h2>

<h3>✓ Perfect For:</h3>
<ul>
<li>Covering bowls and containers</li>
<li>Wrapping cheese, bread, and baked goods</li>
<li>Storing cut fruits and vegetables</li>
<li>Packing sandwiches and snacks</li>
<li>Covering rising bread dough</li>
<li>Creating little pouches for trail mix or crackers</li>
</ul>

<h3>✗ Avoid Using For:</h3>
<ul>
<li>Raw meat or fish (food safety)</li>
<li>Hot foods (wax will melt)</li>
<li>Microwave use</li>
<li>Very wet or acidic foods (may degrade wax faster)</li>
</ul>

<h2>Caring for Your Wraps</h2>

<p>According to <a href="https://www.amesfarm.com/blogs/showcase-ames-farm-honey-retailer/how-switching-to-beeswax-wraps-can-help-save-the-planet" target="_blank" rel="noopener">Ames Farm</a>: "With proper care, beeswax wraps can last up to a year or more." Here's how to maximize their lifespan:</p>

<ul>
<li><strong>Wash</strong> in cool water only—hot water melts the wax</li>
<li><strong>Use mild soap</strong>—avoid harsh detergents</li>
<li><strong>Air dry</strong>—never wring or twist</li>
<li><strong>Store flat or loosely rolled</strong>—avoid sharp folds</li>
<li><strong>Keep away from heat</strong>—don't leave near stoves or in hot cars</li>
</ul>

<h2>Refreshing Old Wraps</h2>

<p>When your wraps start losing their stickiness (usually after 6-12 months), you can refresh them:</p>

<ol>
<li>Place on parchment-lined baking sheet</li>
<li>Sprinkle with fresh beeswax</li>
<li>Warm in oven at 200°F for a few minutes</li>
<li>Spread and cool as before</li>
</ol>

<p>When wraps are truly worn out, simply compost them—they're fully biodegradable!</p>

<h2>The Environmental Impact</h2>

<p>By making the switch to beeswax wraps, you're directly combating plastic pollution. The <a href="https://southernsustainabilityinstitute.org/beeswax-food-wraps-the-eco-friendly-alternative-to-plastic-wrap/" target="_blank" rel="noopener">Southern Sustainability Institute</a> summarizes it beautifully: "Beeswax food wraps are a simple, effective, and eco-friendly solution to the growing problem of plastic waste. By switching to reusable, biodegradable wraps, we can significantly reduce our reliance on single-use plastic, prevent pollution, and support sustainable farming practices."</p>

<p>Consider this: if one family uses just 3 reusable beeswax wraps instead of a roll of plastic wrap every month, that's over 12 rolls of plastic wrap—hundreds of single-use pieces—kept out of landfills each year.</p>

<h2>Vegan Alternative: Candelilla Wax</h2>

<p>If you prefer a vegan option, substitute beeswax with candelilla wax (derived from plants). The process is identical, though candelilla wax is harder, so you may want to add slightly more jojoba oil for flexibility.</p>

<h2>Start Your Plastic-Free Kitchen Today</h2>

<p>Making beeswax wraps is one of the simplest, most satisfying sustainable living projects you can tackle. In less than an hour, you'll have beautiful, functional food wraps that will serve you for months—and every time you reach for one instead of plastic, you're making a difference.</p>

<h2>Resources</h2>

<ul>
<li><a href="https://homesteadandchill.com/diy-homemade-beeswax-wraps/" target="_blank" rel="noopener">Homestead and Chill - DIY Homemade Beeswax Wraps</a></li>
<li><a href="https://southernsustainabilityinstitute.org/beeswax-food-wraps-the-eco-friendly-alternative-to-plastic-wrap/" target="_blank" rel="noopener">Southern Sustainability Institute - Beeswax Food Wraps Guide</a></li>
<li><a href="https://www.amesfarm.com/blogs/showcase-ames-farm-honey-retailer/how-switching-to-beeswax-wraps-can-help-save-the-planet" target="_blank" rel="noopener">Ames Farm - How Beeswax Wraps Help Save the Planet</a></li>
</ul>
"""


def generate_handle(title):
    import random

    handle = title.lower()
    handle = re.sub(r"[^a-z0-9\s-]", "", handle)
    handle = re.sub(r"\s+", "-", handle)
    handle = re.sub(r"-+", "-", handle)
    handle = handle.strip("-")
    suffix = random.randint(1000, 9999)
    return f"{handle}-{suffix}"


def publish_article():
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }

    handle = generate_handle(TOPIC["title"])

    article_data = {
        "article": {
            "title": TOPIC["title"],
            "author": AUTHOR,
            "body_html": BODY_HTML,
            "tags": ", ".join(TOPIC["tags"]),
            "handle": handle,
            "published": True,
            "image": {"src": IMAGES[0]["url"], "alt": IMAGES[0]["alt"][:100]},
        }
    }

    url = (
        f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles.json"
    )

    print(f"📝 Publishing: {TOPIC['title']}")
    print(f"   Handle: {handle}")

    response = requests.post(url, headers=headers, json=article_data, timeout=60)

    if response.status_code == 201:
        article = response.json()["article"]
        article_id = article["id"]
        print(f"   ✅ Created article ID: {article_id}")

        set_seo_metafields(article_id)

        print(f"   🔗 URL: https://{SHOPIFY_STORE}/blogs/sustainable-living/{handle}")
        return article_id
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        return None


def set_seo_metafields(article_id):
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }

    metafields = [
        {
            "key": "title_tag",
            "value": TOPIC["seo_title"],
            "type": "single_line_text_field",
            "namespace": "global",
        },
        {
            "key": "description_tag",
            "value": TOPIC["seo_desc"],
            "type": "single_line_text_field",
            "namespace": "global",
        },
    ]

    for mf in metafields:
        url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/articles/{article_id}/metafields.json"
        response = requests.post(
            url, headers=headers, json={"metafield": mf}, timeout=30
        )
        if response.status_code == 201:
            print(f"   ✅ Set {mf['key']}")


if __name__ == "__main__":
    print("=" * 60)
    print("TOPIC 24: DIY Beeswax Wraps for Food Storage")
    print("=" * 60)
    print()
    print("This article includes:")
    print("✓ EPA statistic: 9 billion pounds of plastic film annually")
    print(
        "✓ Real research from Homestead and Chill, Southern Sustainability Institute, Ames Farm"
    )
    print("✓ Complete step-by-step tutorial (oven + iron methods)")
    print("✓ Comparison table: plastic vs beeswax wraps")
    print("✓ Care and maintenance guide")
    print("✓ 4 high-quality images")
    print()

    article_id = publish_article()

    if article_id:
        print()
        print("=" * 60)
        print("✅ PUBLISHED SUCCESSFULLY!")
        print("=" * 60)
