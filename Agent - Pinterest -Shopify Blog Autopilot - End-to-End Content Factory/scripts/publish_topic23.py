#!/usr/bin/env python3
"""
publish_topic23.py - Publish Topic 23: Composting in Small Spaces
"""

import requests
import re
from datetime import datetime

# ============== CONFIGURATION ==============
SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
API_VERSION = "2025-01"
BLOG_ID = "108441862462"
AUTHOR = "The Rike"

TOPIC = {
    "id": 23,
    "title": "Composting in Small Spaces",
    "seo_title": "Composting in Small Spaces | Apartment Composting Guide",
    "seo_desc": "Start composting even in a tiny apartment! Learn small-space composting methods including bokashi, vermicomposting, and countertop systems.",
    "tags": [
        "composting",
        "apartment living",
        "zero waste",
        "small space gardening",
        "sustainable living",
    ],
}

IMAGES = [
    {
        "url": "https://images.pexels.com/photos/4503273/pexels-photo-4503273.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Small indoor compost bin on kitchen counter with vegetable scraps",
        "photographer": "Pexels",
    },
    {
        "url": "https://images.pexels.com/photos/4750270/pexels-photo-4750270.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Fresh compost soil rich in nutrients for plants",
        "photographer": "Pexels",
    },
    {
        "url": "https://images.pexels.com/photos/4505161/pexels-photo-4505161.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Vegetable peels and fruit scraps for composting",
        "photographer": "Pexels",
    },
    {
        "url": "https://images.pexels.com/photos/4505447/pexels-photo-4505447.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Indoor plants thriving with homemade compost",
        "photographer": "Pexels",
    },
]

BODY_HTML = """
<p>Living in an apartment doesn't mean you have to miss out on composting. In fact, some of the most efficient composting methods are specifically designed for small spaces—and they work beautifully in kitchens, balconies, or even under the sink. Whether you choose worms, fermentation, or electric technology, you can transform your food waste into nutrient-rich gold without ever stepping outside.</p>

<p>The stakes are higher than you might think. According to the <a href="https://www.epa.gov/" target="_blank" rel="noopener">U.S. Environmental Protection Agency (EPA)</a>, food waste makes up approximately <strong>24% of all landfill content</strong>, and landfilled food waste causes an estimated <strong>58% of methane emissions</strong> from landfills. Methane is a greenhouse gas over 25 times more potent than carbon dioxide. By composting at home—even in a tiny apartment—you're making a real difference for the planet.</p>

<figure><img src="https://images.pexels.com/photos/4750270/pexels-photo-4750270.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Fresh compost soil rich in nutrients for plants" loading="lazy" /><figcaption>Photo via Pexels</figcaption></figure>

<h2>Why Compost in Your Apartment?</h2>

<p>As <a href="https://ecofriendlybliss.com/apartment-composting/" target="_blank" rel="noopener">Suraj Shetty from Eco Friendly Bliss</a> explains: "Composting in your apartment helps cut down waste. Plus, you'll shrink your carbon footprint and make nutrient-rich soil for your indoor plants or balcony garden. Every time you toss a banana peel in the compost bin instead of the trash, it feels like you're an eco-volunteer!"</p>

<p>Here's what apartment composting offers:</p>

<ul>
<li><strong>Reduce landfill waste</strong> – In some cities, food waste accounts for over 60% of daily solid waste</li>
<li><strong>Create free fertilizer</strong> – Compost is "black gold" for your houseplants</li>
<li><strong>Lower your carbon footprint</strong> – Diverting food from landfills reduces methane emissions</li>
<li><strong>Connect with nature</strong> – Composting reminds us there is no waste in nature</li>
<li><strong>Save money</strong> – No need to buy fertilizer for your plants</li>
</ul>

<h2>Method 1: Vermicomposting (Worm Composting)</h2>

<p>Vermicomposting uses earthworms—specifically red wigglers (Eisenia fetida)—to digest organic waste. It's ideal for apartments because it creates minimal odor and can be practiced indoors year-round.</p>

<p>As <a href="https://upstartist.tv/blog/beginners-guide-worm-composting-inside-your-apartment/" target="_blank" rel="noopener">Darren from Upstartist</a> notes: "Worm castings are nicknamed 'black gold' because they stimulate plant growth more than any other natural fertilizer. One tablespoon of worm castings provides enough organic nutrients to feed a 6-inch potted plant for 2 months."</p>

<h3>What You Need:</h3>

<ul>
<li>A container with air holes and drainage</li>
<li>Bedding material (shredded newspaper, cardboard, or coconut coir)</li>
<li>Composting worms ("red wigglers" or Eisenia fetida)</li>
<li>Food scraps (fruit and vegetable waste, coffee grounds, tea bags)</li>
</ul>

<figure><img src="https://images.pexels.com/photos/4505161/pexels-photo-4505161.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Vegetable peels and fruit scraps for composting" loading="lazy" /><figcaption>Photo via Pexels</figcaption></figure>

<h3>Processing Capacity</h3>

<p>Each square foot of bin area can process approximately <strong>1 pound of food waste weekly</strong>. The worms consume organic matter, reproduce quickly, and produce nutrient-rich castings. Many systems use stacked trays with holes allowing worms to move upward toward fresh food, making harvesting easier.</p>

<h3>Best Practices:</h3>

<ul>
<li>Keep the bin in a corner of your kitchen for easy access</li>
<li>Feed regularly but don't overfeed</li>
<li>Maintain moist (not wet) bedding</li>
<li><strong>Avoid</strong>: meat, dairy, citrus, onions, and spicy foods</li>
</ul>

<h2>Method 2: Bokashi Fermentation</h2>

<p>Bokashi is a Japanese fermentation-based method that's perfect for apartment dwellers. Unlike traditional composting, bokashi uses an anaerobic (sealed) process that pickles food waste using special microbe-rich bran.</p>

<p>According to <a href="https://www.cmigroupinc.ca/how-to-start-composting-at-home-a-beginners-guide/" target="_blank" rel="noopener">CMI Group</a>: "Unlike traditional composting, bokashi accepts virtually all kitchen waste—including meat, dairy, and oils—without creating odors or attracting pests."</p>

<h3>Key Benefits:</h3>

<table style="width:100%; border-collapse: collapse; margin: 1rem 0;">
<tr style="background-color: #f8f8f8;">
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Feature</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Bokashi Advantage</th>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Speed</td>
<td style="padding: 12px; border: 1px solid #ddd;">4-6 weeks total (2 weeks fermentation + burial)</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;">Accepts</td>
<td style="padding: 12px; border: 1px solid #ddd;">ALL kitchen waste including meat, dairy, oils</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Space Needed</td>
<td style="padding: 12px; border: 1px solid #ddd;">Just a small bucket under the sink</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;">Odor</td>
<td style="padding: 12px; border: 1px solid #ddd;">Slight pickle smell (sealed system)</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Pests</td>
<td style="padding: 12px; border: 1px solid #ddd;">None—acidic fermented matter repels vermin</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;">Bonus</td>
<td style="padding: 12px; border: 1px solid #ddd;">Produces "compost tea" for fertilizer or drain cleaning</td>
</tr>
</table>

<h3>How Bokashi Works:</h3>

<ol>
<li>Layer food scraps in an airtight bokashi bucket</li>
<li>Sprinkle bokashi bran over each layer</li>
<li>Press down to remove air and seal</li>
<li>Drain the "compost tea" every few days</li>
<li>After 2 weeks, bury the fermented matter in soil or a planter</li>
<li>Wait 2-4 more weeks for complete decomposition</li>
</ol>

<h2>Method 3: Electric Composters</h2>

<p>If worms aren't your thing and fermentation sounds complicated, electric composters offer a push-button solution. These countertop devices grind and dry food scraps into a soil-like material in just a few hours.</p>

<p>As noted by <a href="https://ecofriendlybliss.com/apartment-composting/" target="_blank" rel="noopener">Eco Friendly Bliss</a>: "These machines are odor-free, pest-proof, and capable of processing most kitchen waste—including small bones and dairy."</p>

<figure><img src="https://images.pexels.com/photos/4505447/pexels-photo-4505447.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Indoor plants thriving with homemade compost" loading="lazy" /><figcaption>Photo via Pexels</figcaption></figure>

<h3>Electric Composter Pros and Cons:</h3>

<p><strong>Pros:</strong></p>
<ul>
<li>Fast—just a few hours</li>
<li>No maintenance required</li>
<li>Accepts meat, dairy, and bones</li>
<li>Completely odor-free</li>
</ul>

<p><strong>Cons:</strong></p>
<ul>
<li>Higher upfront cost ($200-400)</li>
<li>Uses electricity</li>
<li>Produces dried material that still needs soil time to become true compost</li>
</ul>

<h2>Choosing the Right Method for Your Space</h2>

<table style="width:100%; border-collapse: collapse; margin: 1rem 0;">
<tr style="background-color: #f8f8f8;">
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Method</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Best For</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Limitations</th>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Vermicomposting</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">Indoor gardeners, plant lovers, regular veggie scraps</td>
<td style="padding: 12px; border: 1px solid #ddd;">No meat, dairy, or citrus</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Bokashi</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">Small kitchens, mixed food waste, apartments</td>
<td style="padding: 12px; border: 1px solid #ddd;">Need outdoor soil to finish decomposition</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Electric</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">Busy households, no outdoor access, hands-off</td>
<td style="padding: 12px; border: 1px solid #ddd;">Higher cost, uses electricity</td>
</tr>
</table>

<h2>What Can You Compost in an Apartment?</h2>

<h3>✓ Compostable Items (All Methods)</h3>
<ul>
<li>Fruit and vegetable scraps</li>
<li>Coffee grounds and filters</li>
<li>Tea bags (remove staples)</li>
<li>Eggshells (crushed)</li>
<li>Bread and grains</li>
<li>Paper towels and napkins</li>
<li>Cardboard (shredded)</li>
</ul>

<h3>✓ Bokashi & Electric Only</h3>
<ul>
<li>Meat and fish scraps</li>
<li>Dairy products</li>
<li>Cooked food leftovers</li>
<li>Small bones</li>
<li>Oils and fats (small amounts)</li>
</ul>

<h3>✗ Never Compost</h3>
<ul>
<li>Pet waste</li>
<li>Diseased plants</li>
<li>Plastic or synthetic materials</li>
<li>Glossy printed paper</li>
</ul>

<h2>Setting Up Your Composting Area</h2>

<p>Finding the right spot is essential for success:</p>

<ol>
<li><strong>Easy access</strong> – Near where you prepare food (kitchen counter or under sink)</li>
<li><strong>Avoid direct sun</strong> – Prevents overheating</li>
<li><strong>Good ventilation</strong> – For worm bins especially</li>
<li><strong>Stable temperature</strong> – Worms prefer 55-77°F (13-25°C)</li>
</ol>

<p>As one apartment composter shares: "I've placed my vermicomposting bin in a corner of my kitchen so it's easy to add scraps while I cook!"</p>

<h2>Troubleshooting Common Issues</h2>

<table style="width:100%; border-collapse: collapse; margin: 1rem 0;">
<tr style="background-color: #f8f8f8;">
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Problem</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Cause</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Solution</th>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Bad smell</td>
<td style="padding: 12px; border: 1px solid #ddd;">Too wet or too much green material</td>
<td style="padding: 12px; border: 1px solid #ddd;">Add dry brown materials (cardboard, paper)</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;">Fruit flies</td>
<td style="padding: 12px; border: 1px solid #ddd;">Exposed food scraps</td>
<td style="padding: 12px; border: 1px solid #ddd;">Bury scraps under bedding; freeze before adding</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;">Worms escaping</td>
<td style="padding: 12px; border: 1px solid #ddd;">Conditions too wet, acidic, or hot</td>
<td style="padding: 12px; border: 1px solid #ddd;">Adjust moisture; add crushed eggshells</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;">Slow decomposition</td>
<td style="padding: 12px; border: 1px solid #ddd;">Too dry or not enough worms</td>
<td style="padding: 12px; border: 1px solid #ddd;">Add moisture; give worms time to multiply</td>
</tr>
</table>

<h2>Using Your Finished Compost</h2>

<p>Once your compost is ready (dark, crumbly, earthy-smelling), you can:</p>

<ul>
<li><strong>Top-dress houseplants</strong> – Add a thin layer on top of soil</li>
<li><strong>Mix into potting soil</strong> – Create rich planting mix for repotting</li>
<li><strong>Feed balcony gardens</strong> – Perfect for container vegetables and herbs</li>
<li><strong>Share with friends</strong> – Gift plant-loving neighbors some "black gold"</li>
<li><strong>Donate to community gardens</strong> – Many accept compost contributions</li>
</ul>

<h2>Start Composting Today</h2>

<p>No matter how small your living space, there's a composting method that fits. Start with just a small countertop container for collecting daily scraps, then choose the system that matches your lifestyle. With every banana peel and coffee filter you divert from the landfill, you're making a meaningful impact on our planet's health.</p>

<h2>Resources</h2>

<ul>
<li><a href="https://www.epa.gov/sustainable-management-food/types-composting-and-understanding-process" target="_blank" rel="noopener">EPA Guide to Composting</a></li>
<li><a href="https://ecofriendlybliss.com/apartment-composting/" target="_blank" rel="noopener">Eco Friendly Bliss - Complete Apartment Composting Guide</a></li>
<li><a href="https://upstartist.tv/blog/beginners-guide-worm-composting-inside-your-apartment/" target="_blank" rel="noopener">Upstartist - Worm Composting in Apartments</a></li>
<li><a href="https://www.rovetravel.com/blog/apartment-composting-guide" target="_blank" rel="noopener">Rove Travel - Apartment Composting Guide</a></li>
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
    print("TOPIC 23: Composting in Small Spaces")
    print("=" * 60)
    print()
    print("This article includes:")
    print("✓ EPA statistics on food waste and methane emissions")
    print("✓ 3 complete methods: Vermicomposting, Bokashi, Electric")
    print("✓ Expert quotes and real research")
    print("✓ Comparison tables and troubleshooting")
    print("✓ 4 high-quality images")
    print()

    article_id = publish_article()

    if article_id:
        print()
        print("=" * 60)
        print("✅ PUBLISHED SUCCESSFULLY!")
        print("=" * 60)
