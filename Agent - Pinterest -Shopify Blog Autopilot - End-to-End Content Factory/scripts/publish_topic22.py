#!/usr/bin/env python3
"""
publish_topic22.py - Publish Topic 22: Growing Herbs Indoors Year-Round
"""

import requests
import re
import json
from datetime import datetime

# ============== CONFIGURATION ==============
SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
API_VERSION = "2025-01"
BLOG_ID = "108441862462"
AUTHOR = "The Rike"

TOPIC = {
    "id": 22,
    "title": "Growing Herbs Indoors Year-Round",
    "seo_title": "Growing Herbs Indoors Year-Round | Indoor Herb Garden Guide",
    "seo_desc": "Grow fresh herbs indoors all year! Complete guide to starting an indoor herb garden with tips on light, water, and the best herbs for windowsill growing.",
    "tags": [
        "indoor herbs",
        "herb garden",
        "indoor gardening",
        "kitchen herbs",
        "sustainable living",
    ],
}

IMAGES = [
    {
        "url": "https://images.pexels.com/photos/4503273/pexels-photo-4503273.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Fresh herbs growing in pots on a sunny windowsill",
        "photographer": "Pexels",
    },
    {
        "url": "https://images.pexels.com/photos/4503261/pexels-photo-4503261.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Basil plants thriving in an indoor herb garden",
        "photographer": "Pexels",
    },
    {
        "url": "https://images.pexels.com/photos/5137625/pexels-photo-5137625.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Hands harvesting fresh herbs from potted plants",
        "photographer": "Pexels",
    },
    {
        "url": "https://images.pexels.com/photos/4750274/pexels-photo-4750274.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Kitchen windowsill with variety of potted herbs",
        "photographer": "Pexels",
    },
]

BODY_HTML = """
<p>Imagine stepping into your kitchen on a cold winter morning and snipping fresh basil for your pasta, or plucking mint leaves for your afternoon tea—without ever leaving your home. Growing herbs indoors year-round isn't just possible; it's one of the most rewarding sustainable living practices you can adopt. With the right setup, your windowsill can become a thriving mini garden that delivers fresh flavor and green beauty every single day.</p>

<p>According to <a href="https://www.marthastewart.com/1537621/guide-growing-kitchen-windowsill-herbs" target="_blank" rel="noopener">gardening expert Melinda Myers</a>, host of the Great Courses "How to Grow Anything" DVD series, "Most herbs need 6 to 8 hours of bright light" to thrive indoors. Understanding these basic requirements is your first step to success.</p>

<figure><img src="https://images.pexels.com/photos/4503261/pexels-photo-4503261.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Basil plants thriving in an indoor herb garden" loading="lazy" /><figcaption>Photo via Pexels</figcaption></figure>

<h2>Why Start an Indoor Herb Garden?</h2>

<p>An indoor herb garden offers benefits that extend far beyond fresh seasoning. As the team at <a href="https://goebbertspumpkinfarm.com/growing-an-indoor-herb-garden/" target="_blank" rel="noopener">Goebbert's Farm & Garden Center</a> notes: "An indoor herb garden offers unmatched convenience and charm. You're no longer tied to the seasons or the grocery store when it comes to flavor. Fresh herbs are always within reach—ready to snip into soups, sauces, and teas."</p>

<p>Here's what you gain:</p>

<ul>
<li><strong>Year-round fresh flavor</strong> without grocery store trips or seasonal limitations</li>
<li><strong>Cost savings</strong>—growing from seed costs a fraction of buying fresh herbs weekly</li>
<li><strong>Better nutrition</strong>—herbs are richest in essential oils and nutrients when freshly picked</li>
<li><strong>Reduced plastic waste</strong> from store-bought herb packaging</li>
<li><strong>Therapeutic benefits</strong>—tending plants reduces stress and improves mood</li>
<li><strong>Educational opportunity</strong> for teaching children about plant care and where food comes from</li>
</ul>

<h2>The Best Herbs for Indoor Growing</h2>

<p>Not all herbs adapt equally well to indoor conditions. According to <a href="https://www.tastingtable.com/1945318/indoor-herb-garden-tips/" target="_blank" rel="noopener">Tasting Table</a>, "Basil, mint, parsley, chives, and thyme are considered the easiest herbs to grow indoors." Here's your complete guide to the best performers:</p>

<h3>Sun-Loving Herbs (6-8 Hours Light)</h3>

<table style="width:100%; border-collapse: collapse; margin: 1rem 0;">
<tr style="background-color: #f8f8f8;">
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Herb</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Time to Harvest</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Best Uses</th>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Basil</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">28 days</td>
<td style="padding: 12px; border: 1px solid #ddd;">Pasta, pesto, caprese</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Thyme</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">6-8 weeks</td>
<td style="padding: 12px; border: 1px solid #ddd;">Roasted vegetables, meats</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Oregano</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">6-8 weeks</td>
<td style="padding: 12px; border: 1px solid #ddd;">Italian dishes, pizza</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Rosemary</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">8-10 weeks</td>
<td style="padding: 12px; border: 1px solid #ddd;">Focaccia, roasted potatoes</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Sage</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">6-8 weeks</td>
<td style="padding: 12px; border: 1px solid #ddd;">Stuffing, butter sauce</td>
</tr>
</table>

<figure><img src="https://images.pexels.com/photos/5137625/pexels-photo-5137625.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Hands harvesting fresh herbs from potted plants" loading="lazy" /><figcaption>Photo via Pexels</figcaption></figure>

<h3>Shade-Tolerant Herbs (4-6 Hours Light)</h3>

<p>If you don't have a south-facing window, don't worry. These herbs thrive in partial shade:</p>

<ul>
<li><strong>Parsley</strong> – Easy to maintain, adds fresh finish to meals</li>
<li><strong>Chives</strong> – Quick growing, useful in countless dishes</li>
<li><strong>Mint</strong> – Hardy and fast-growing (give it its own pot!)</li>
<li><strong>Cilantro</strong> – Prefers cooler temperatures and shade</li>
<li><strong>Lemon Balm</strong> – Thrives in shadier spots</li>
</ul>

<p>As noted by <a href="https://risegardens.com/blogs/communitygarden/the-complete-beginners-guide-to-indoor-herb-gardening-s25" target="_blank" rel="noopener">Rise Gardens</a>: "Basil is ready to harvest in just 28 days and delivers continuous harvests when you pinch leaves from stem tips."</p>

<h2>Setting Up Your Indoor Herb Garden: Step by Step</h2>

<h3>Step 1: Choose the Right Location</h3>

<p>A south-facing window offers the best chance of full sunlight in the northern hemisphere. If natural light is limited, consider using grow lights to supplement. All herbs require a <strong>minimum of four hours of sunlight per day</strong>, with sun-loving plants needing between six and eight hours.</p>

<h3>Step 2: Select Proper Containers</h3>

<p>Use pots with <strong>drainage holes</strong> to prevent root rot—this is non-negotiable. Place a saucer underneath each pot to catch runoff. Terra cotta pots are excellent choices as they allow soil to breathe, though they require more frequent watering.</p>

<h3>Step 3: Use Quality Potting Mix</h3>

<p>Never use outdoor garden soil, which can compact and harbor pests. Choose a well-draining indoor potting mix specifically formulated for containers. Some herbs like rosemary prefer even grittier, faster-draining soil.</p>

<h3>Step 4: Master the Watering Schedule</h3>

<p>Most herb problems come from overwatering. Water only when the <strong>top inch of soil feels dry</strong>. Water thoroughly until it drains from the bottom, then empty the saucer after 30 minutes to prevent root rot.</p>

<figure><img src="https://images.pexels.com/photos/4750274/pexels-photo-4750274.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Kitchen windowsill with variety of potted herbs" loading="lazy" /><figcaption>Photo via Pexels</figcaption></figure>

<h3>Step 5: Rotate and Fertilize</h3>

<p>Rotate pots weekly for even growth—plants naturally lean toward light. Feed your herbs with an organic fertilizer every few weeks for consistent health and flavor. Be gentle; herbs don't need heavy feeding.</p>

<h2>Harvesting for Maximum Growth</h2>

<p>Proper harvesting technique actually encourages your plants to grow more. As plant expert <em>Sam Tall</em> explains: "Sometimes removing just 1 or 2 inches from the ends will encourage the lower nodes to fill out and push new growth, making the plant look fuller." He adds that removing old flowers will "trick the plant into thinking it hasn't set seed. This can encourage new blooms or fresh growth."</p>

<p>Follow these harvesting best practices:</p>

<ul>
<li>Wait until herbs reach <strong>6-8 inches tall</strong> before first harvest</li>
<li>Snip just above a <strong>leaf node</strong> (where leaves meet the stem)</li>
<li>Never cut more than <strong>one-third of the plant</strong> at once</li>
<li>Harvest in the <strong>morning</strong> for peak oil content and best flavor</li>
<li>For mint, you can harvest up to 1/4 of the plant at once—it's that resilient!</li>
</ul>

<h2>Troubleshooting Common Problems</h2>

<p>Even experienced gardeners face challenges. Here's how to diagnose and fix common issues:</p>

<table style="width:100%; border-collapse: collapse; margin: 1rem 0;">
<tr style="background-color: #f8f8f8;">
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Problem</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Cause</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Solution</th>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Leggy, stretched growth</td>
<td style="padding: 12px; border: 1px solid #ddd;">Insufficient light</td>
<td style="padding: 12px; border: 1px solid #ddd;">Move closer to window or add grow lights</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;">Yellowing leaves</td>
<td style="padding: 12px; border: 1px solid #ddd;">Overwatering</td>
<td style="padding: 12px; border: 1px solid #ddd;">Let soil dry out between waterings</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Mold on soil surface</td>
<td style="padding: 12px; border: 1px solid #ddd;">Poor airflow/overwatering</td>
<td style="padding: 12px; border: 1px solid #ddd;">Improve ventilation, water less</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;">Slow growth</td>
<td style="padding: 12px; border: 1px solid #ddd;">Root-bound or needs nutrients</td>
<td style="padding: 12px; border: 1px solid #ddd;">Repot or apply organic fertilizer</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Brown leaf tips</td>
<td style="padding: 12px; border: 1px solid #ddd;">Low humidity or salt buildup</td>
<td style="padding: 12px; border: 1px solid #ddd;">Mist regularly or flush soil</td>
</tr>
</table>

<h2>Save Money by Starting from Seed</h2>

<p>As <a href="https://www.tastingtable.com/1945318/indoor-herb-garden-tips/" target="_blank" rel="noopener">Tasting Table</a> points out: "Starting an indoor herb garden can be costly. By the time you've bought pots, potting soil, and food, you already have quite a hefty bill. Buying herb seedlings can make it even more expensive. A more affordable option is to grow your own from seed."</p>

<p>To start from seed:</p>

<ol>
<li>Fill a container with moist potting mix</li>
<li>Pat it down until flat</li>
<li>Sprinkle a few seeds on the surface</li>
<li>Cover lightly with a thin layer of soil</li>
<li>Mist gently with water</li>
<li>Place in a warm, sunny spot</li>
<li>Keep soil consistently moist</li>
<li>Label your seedlings!</li>
</ol>

<p>Once seedlings are large enough to handle, transplant into individual pots. You'll have your own thriving herb garden for a fraction of the cost.</p>

<h2>Cooking with Your Harvest</h2>

<p>The reward for all your care is incredible flavor in your cooking. Here are some ideas to get you started:</p>

<ul>
<li><strong>Basil</strong> – Fresh pesto, caprese salad, pasta sauce</li>
<li><strong>Mint</strong> – Homemade lemonade, cocktails, lamb dishes</li>
<li><strong>Rosemary</strong> – Focaccia bread, roasted potatoes, grilled meats</li>
<li><strong>Thyme</strong> – Soups, stews, roasted vegetables</li>
<li><strong>Parsley</strong> – Fresh garnish, tabbouleh, chimichurri</li>
<li><strong>Chives</strong> – Baked potatoes, eggs, cream cheese dips</li>
</ul>

<h2>Beyond the Basics: Exotic Herbs</h2>

<p>Once you've mastered the classics, consider expanding to harder-to-find varieties. As Rise Gardens suggests: "Why not venture beyond the ordinary and cultivate herbs that are hard to find at your local grocery store?" Consider Thai basil for curries, lemongrass for soups, or fenugreek for Indian cuisine. Your indoor garden can become "a treasure trove of exciting flavors from around the world."</p>

<h2>Pet Safety Note</h2>

<p>If you have pets, be aware that certain herbs can be toxic to cats and dogs. Keep chives, bay laurel, and concentrated essential oil herbs out of reach. Always research before adding new plants to your pet-friendly home.</p>

<h2>Resources for Continued Learning</h2>

<ul>
<li><a href="https://extension.psu.edu/" target="_blank" rel="noopener">Penn State Extension</a> – Year-round gardening resources</li>
<li><a href="https://www.marthastewart.com/1537621/guide-growing-kitchen-windowsill-herbs" target="_blank" rel="noopener">Martha Stewart</a> – Windowsill Herb Garden Guide</li>
<li><a href="https://www.tastingtable.com/1945318/indoor-herb-garden-tips/" target="_blank" rel="noopener">Tasting Table</a> – 15 Tips for Indoor Herb Gardens</li>
<li><a href="https://risegardens.com/blogs/communitygarden/the-complete-beginners-guide-to-indoor-herb-gardening-s25" target="_blank" rel="noopener">Rise Gardens</a> – Complete Beginner's Guide</li>
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
    print("TOPIC 22: Growing Herbs Indoors Year-Round")
    print("=" * 60)
    print()
    print("This article includes:")
    print(
        "✓ Real research from Martha Stewart, Tasting Table, Rise Gardens, Goebbert's"
    )
    print("✓ Expert quotes from Melinda Myers and Sam Tall")
    print("✓ Detailed herb tables with harvest times")
    print("✓ Step-by-step setup guide")
    print("✓ Troubleshooting common problems")
    print("✓ 4 high-quality images")
    print()

    article_id = publish_article()

    if article_id:
        print()
        print("=" * 60)
        print("✅ PUBLISHED SUCCESSFULLY!")
        print("=" * 60)
