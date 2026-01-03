#!/usr/bin/env python3
"""
publish_topic21.py - Publish Topic 21: Natural Fabric Dyes from Food Scraps

This script publishes a HIGH-QUALITY article following the SHOPIFY BLOG META-PROMPT:
- Real research with citations
- Expert quotes
- Statistical data
- 4 images (1 main + 3 inline)
- Proper SEO meta fields
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

# Topic 21 metadata
TOPIC = {
    "id": 21,
    "title": "Natural Fabric Dyes from Food Scraps",
    "seo_title": "Natural Fabric Dyes from Food Scraps | Eco-Friendly Dyeing Guide",
    "seo_desc": "Create beautiful natural fabric dyes from kitchen scraps! Learn to dye fabric with avocado pits, onion skins, turmeric and more eco-friendly ingredients.",
    "tags": [
        "natural dyes",
        "fabric dyeing",
        "food scraps",
        "sustainable fashion",
        "eco crafts",
    ],
}

# Images from Pexels search
IMAGES = [
    {
        "url": "https://images.pexels.com/photos/14382181/pexels-photo-14382181.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Colorful fabrics drying after natural dyeing process",
        "photographer": "Adreyat Hasan",
    },
    {
        "url": "https://images.pexels.com/photos/6851168/pexels-photo-6851168.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Shibori technique creating beautiful patterns on naturally dyed fabric",
        "photographer": "Teona Swift",
    },
    {
        "url": "https://images.pexels.com/photos/6850697/pexels-photo-6850697.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Artisan workspace with wooden tools and shibori textile techniques",
        "photographer": "Teona Swift",
    },
    {
        "url": "https://images.pexels.com/photos/35436953/pexels-photo-35436953.jpeg?auto=compress&cs=tinysrgb&h=650&w=940",
        "alt": "Traditional natural dyeing process in action",
        "photographer": "Pexels User",
    },
]

# ============== ARTICLE CONTENT ==============
# This content is based on REAL RESEARCH from web search

BODY_HTML = """
<p>Every time you peel an avocado, chop an onion, or grate fresh turmeric, you're throwing away potential treasure. Those humble kitchen scraps can transform plain fabrics into stunning, naturally colored textiles that are gentle on both your skin and the planet. Natural fabric dyeing isn't just a craft—it's a movement toward sustainable fashion that reduces waste while creating one-of-a-kind pieces.</p>

<p>According to the <a href="https://www.unep.org/" target="_blank" rel="noopener">United Nations Environment Programme (UNEP)</a>, textile dyeing is responsible for <strong>20% of global industrial water pollution</strong>. By switching to natural dyes made from food scraps, you can create beautiful fabrics while dramatically reducing your environmental footprint.</p>

<figure><img src="https://images.pexels.com/photos/6851168/pexels-photo-6851168.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Shibori technique creating beautiful patterns on naturally dyed fabric" loading="lazy" /><figcaption>Photo by Teona Swift on Pexels</figcaption></figure>

<h2>Why Choose Natural Dyes Over Synthetic?</h2>

<p>The fashion industry's reliance on synthetic dyes comes at a tremendous environmental cost. The <a href="https://www.worldbank.org/" target="_blank" rel="noopener">World Bank</a> has identified <strong>over 70 toxic chemicals</strong> that come solely from textile dyeing, many of which are carcinogenic or harmful to aquatic life.</p>

<p>Consider these sobering statistics:</p>

<ul>
<li><strong>90% of textiles</strong> today use synthetic dyes made from petroleum</li>
<li>Dyeing <strong>one kilogram of fabric can require up to 150 liters of water</strong></li>
<li>Synthetic dyes often contain heavy metals, formaldehyde, and chlorine compounds</li>
</ul>

<p>As <em>Nicky Crane from Thread Collective</em> explains: "Dyeing with kitchen scraps is not just eco-friendly; it's a creative way to connect with nature and your materials. By repurposing waste, you avoid synthetic chemicals and reduce your environmental footprint while saving money."</p>

<h2>Your Kitchen Scrap Color Palette</h2>

<p>The range of colors you can achieve from everyday food waste is remarkable. Here's your complete guide to building a natural dye palette:</p>

<h3>Pinks and Peachy Tones</h3>
<p><strong>Avocado pits and skins</strong> are perhaps the most surprising natural dye source. While you'd expect green, they actually produce soft pinks and peach tones. Clean pits and skins thoroughly, store them in an airtight container, and freeze until ready to use.</p>

<figure><img src="https://images.pexels.com/photos/6850697/pexels-photo-6850697.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Artisan workspace with wooden tools and natural dyeing materials" loading="lazy" /><figcaption>Photo by Teona Swift on Pexels</figcaption></figure>

<h3>Yellows and Golden Orange</h3>
<p><strong>Yellow onion skins</strong> are perfect for beginners. They produce vibrant yellows and golden-orange hues. Simply save the outer papery layers when peeling onions and store them in a dry jar or paper bag.</p>

<p><strong>Turmeric</strong> creates bright, sunshine yellow tones. Fresh or powdered turmeric both work wonderfully, though be aware this dye can be less lightfast than others.</p>

<h3>Browns and Earth Tones</h3>
<p><strong>Coffee grounds</strong> produce warm brown tones perfect for creating an antique or vintage look. Collect used grounds, dry them thoroughly, and store in an airtight container to prevent mold. <strong>Black tea</strong> creates light beige to warm brown shades and doesn't require a mordant due to its high tannin content.</p>

<h3>Purples and Blues</h3>
<p><strong>Red cabbage</strong> is truly magical—it produces purples and blues depending on the pH of your dye bath. Save the outer leaves and scraps, refrigerate for short-term use, or freeze for later projects.</p>

<h2>The Natural Dyeing Process: Step by Step</h2>

<p>Success with natural dyes follows an 8-step process, as taught by natural dye educator <em>Victoria from La Creative Mama</em>: "For best results you will always need to go through a complete process. Please note that all natural dyes will only work when you use natural fabric or yarn."</p>

<h3>Step 1: Choose the Right Fabric</h3>
<p>Natural dyes work only on <strong>100% natural fibers</strong>—cotton, linen, wool, and silk. Synthetic fabrics won't absorb natural dyes properly. Look for undyed, unbleached fabrics for the best results.</p>

<h3>Step 2: Scour Your Fabric</h3>
<p>Before dyeing, remove any oils, dirt, or finishes from your fabric. Wash in hot water with a natural soap, then rinse thoroughly.</p>

<h3>Step 3: Mordant (When Needed)</h3>
<p>A mordant is a metallic salt that helps natural dye bond to fabric. According to <a href="https://naturaldyes.ca/" target="_blank" rel="noopener">Maiwa's Guide to Natural Dyes</a>, alum is the most common and safest mordant for beginners. However, some dyes like avocado contain natural tannins and don't require additional mordanting.</p>

<figure><img src="https://images.pexels.com/photos/35436953/pexels-photo-35436953.jpeg?auto=compress&cs=tinysrgb&h=650&w=940" alt="Traditional natural fabric dyeing process" loading="lazy" /><figcaption>Photo via Pexels</figcaption></figure>

<h3>Step 4: Create Your Dye Bath</h3>
<p>Place your food scraps in a large pot with water. Use approximately <strong>225g of dyestuff per 450g of fiber</strong>. Simmer (not boil) for 1-4 hours—the longer you simmer, the more intense the color. Strain out the scraps.</p>

<h3>Step 5: Dye Your Fabric</h3>
<p>Wet your mordanted fabric and add it to the dye bath. Simmer gently for 30 minutes to several hours, stirring occasionally for even color. The longer you leave it, the deeper the shade.</p>

<h3>Step 6: Rinse and Dry</h3>
<p>Remove fabric, rinse in cool water until water runs clear, and hang to dry away from direct sunlight to prevent fading.</p>

<h2>Avocado Dyeing: A Detailed Tutorial</h2>

<p>Avocado dyeing deserves special attention because it's beginner-friendly and produces unexpected, gorgeous results:</p>

<ol>
<li>Save peels and pits from about 6 avocados</li>
<li>Clean thoroughly and place in 4-5 cups of water</li>
<li>Simmer (not boil) for 3-4 hours, checking occasionally</li>
<li>Remove dyed water and place in a glass container</li>
<li>Submerge white natural-fiber fabric and soak overnight</li>
<li>Remove, dry, then rinse to remove any residue</li>
</ol>

<p>As <a href="https://www.thistle.co/" target="_blank" rel="noopener">Thistle</a> points out: "Since avocado has naturally-occurring tannins, you don't need to use a mordant when making natural dye with avocado skin and peels. So simple!"</p>

<h2>Complete Color Guide: Food Scraps Rainbow</h2>

<p>Here's your comprehensive reference for creating a full spectrum of natural colors:</p>

<table style="width:100%; border-collapse: collapse; margin: 1rem 0;">
<tr style="background-color: #f8f8f8;">
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Color</th>
<th style="padding: 12px; text-align: left; border: 1px solid #ddd;">Food Scraps</th>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Red/Pink</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">Beet peels, cherries, raspberries, avocado pits</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Orange</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">Paprika, red onion skins, carrot tops</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Yellow</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">Lemon peels, pomegranate peels, turmeric, yellow onion skins</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Green</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">Artichokes, fresh herbs, spinach</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Blue</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">Blueberries, red cabbage (with baking soda)</td>
</tr>
<tr style="background-color: #f8f8f8;">
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Purple</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">Blackberries, red cabbage leaves</td>
</tr>
<tr>
<td style="padding: 12px; border: 1px solid #ddd;"><strong>Brown</strong></td>
<td style="padding: 12px; border: 1px solid #ddd;">Coffee grounds, black tea, walnut hulls</td>
</tr>
</table>

<h2>Project Ideas for Your Naturally Dyed Fabrics</h2>

<p>Once you've mastered the basics, here are inspiring projects to try:</p>

<ul>
<li><strong>Tie-dye scarves</strong> using onion skins or red cabbage for bold patterns</li>
<li><strong>Eco-friendly tote bags</strong> with earthy tones from coffee or tea</li>
<li><strong>Pillowcases</strong> in soft pastels from avocado pits</li>
<li><strong>Linen napkins</strong> in natural, elegant earth tones</li>
<li><strong>Canvas sneakers</strong> refreshed with a custom pink from avocado</li>
</ul>

<h2>Tips for Long-Lasting Natural Colors</h2>

<p>To maximize the longevity of your naturally dyed fabrics:</p>

<ul>
<li>Wash in cold water with mild, natural soap</li>
<li>Avoid direct sunlight when drying</li>
<li>Store away from light to prevent fading</li>
<li>Accept that natural dyes will gently fade over time—this is part of their beauty</li>
<li>Consider iron water as an afterbath to "sadden" and set colors</li>
</ul>

<h2>The Environmental Impact of Your Choice</h2>

<p>By choosing natural dyes, you're making a powerful environmental statement. Brands like <strong>Aizome</strong> are leading the way—their herbal dyes are so clean, they're certified as medical-grade by the U.S. FDA. Companies like <strong>Nature Coatings</strong> have created carbon-negative dyes from wood waste.</p>

<p>As the fashion industry evolves, natural dyeing from food scraps represents both a return to ancestral practices and a path toward a more sustainable future. Every avocado pit saved from the landfill, every onion skin collected, is a small act of environmental stewardship.</p>

<h2>Further Reading</h2>

<ul>
<li><a href="https://threadcollective.com.au/blogs/dyeing/natural-dyeing-kitchen-scraps" target="_blank" rel="noopener">Natural Dyeing with Kitchen Scraps - Thread Collective</a></li>
<li><a href="https://lacreativemama.com/how-to-make-natural-dye/" target="_blank" rel="noopener">How to Make Natural Dye from Foods Scraps - La Creative Mama</a></li>
<li><a href="https://naturaldyes.ca/instructions" target="_blank" rel="noopener">Guide to Natural Dyes - Maiwa</a></li>
<li><a href="https://www.thistle.co/learn/thistle-thoughts/make-natural-dye-from-food-waste" target="_blank" rel="noopener">Natural Dyes from Food Waste - Thistle</a></li>
</ul>
"""


def generate_handle(title):
    """Generate URL handle from title with timestamp"""
    import random

    handle = title.lower()
    handle = re.sub(r"[^a-z0-9\s-]", "", handle)
    handle = re.sub(r"\s+", "-", handle)
    handle = re.sub(r"-+", "-", handle)
    handle = handle.strip("-")
    suffix = random.randint(1000, 9999)
    return f"{handle}-{suffix}"


def publish_article():
    """Publish the article to Shopify"""
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

        # Set SEO metafields
        set_seo_metafields(article_id)

        print(f"   🔗 URL: https://{SHOPIFY_STORE}/blogs/sustainable-living/{handle}")
        return article_id
    else:
        print(f"   ❌ Failed: {response.status_code}")
        print(f"   {response.text}")
        return None


def set_seo_metafields(article_id):
    """Set SEO title and description"""
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
        else:
            print(f"   ⚠️ Failed to set {mf['key']}: {response.status_code}")


if __name__ == "__main__":
    print("=" * 60)
    print("TOPIC 21: Natural Fabric Dyes from Food Scraps")
    print("=" * 60)
    print()
    print("This article includes:")
    print("✓ Real research from Thread Collective, La Creative Mama, Maiwa, Thistle")
    print("✓ UNEP and World Bank statistics")
    print("✓ Expert quotes from natural dye educators")
    print("✓ Step-by-step tutorial")
    print("✓ 4 high-quality images from Pexels")
    print()

    article_id = publish_article()

    if article_id:
        print()
        print("=" * 60)
        print("✅ PUBLISHED SUCCESSFULLY!")
        print("=" * 60)
