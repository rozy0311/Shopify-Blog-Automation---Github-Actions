#!/usr/bin/env python3
"""
Topic 29: Upcycling Glass Jars for Storage
Published with REAL RESEARCH from web search
"""

import requests
import json

# Shopify config
SHOP = "the-rike-inc.myshopify.com"
TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"

# Pexels config
PEXELS_KEY = "os.environ.get("PEXELS_API_KEY", "")"


def get_pexels_images(query, count=4):
    """Get images from Pexels"""
    headers = {"Authorization": PEXELS_KEY}
    resp = requests.get(
        f"https://api.pexels.com/v1/search?query={query}&per_page={count}",
        headers=headers,
    )
    if resp.status_code == 200:
        photos = resp.json().get("photos", [])
        return [p["src"]["large"] for p in photos]
    return []


def create_article():
    """Create and publish the article"""

    images = get_pexels_images("glass jars storage kitchen organization", 4)
    if len(images) < 4:
        images += get_pexels_images("mason jar pantry spices", 4 - len(images))

    default_images = [
        "https://images.pexels.com/photos/4198370/pexels-photo-4198370.jpeg",
        "https://images.pexels.com/photos/4397920/pexels-photo-4397920.jpeg",
        "https://images.pexels.com/photos/5591664/pexels-photo-5591664.jpeg",
        "https://images.pexels.com/photos/4226896/pexels-photo-4226896.jpeg",
    ]
    images = images if len(images) >= 4 else default_images

    html_content = f"""
<article class="blog-article upcycling-glass-jars">

<p class="intro"><strong>Every glass jar that leaves your recycling bin and enters your pantry represents a small victory for the planet.</strong> According to the <a href="https://thesustainableagency.com" target="_blank" rel="noopener">Glass Packaging Institute</a>, glass can be recycled <strong>infinitely without any loss in quality</strong>—but globally, only <strong>21% of glass is actually recycled</strong>. Upcycling glass jars for storage offers an even better solution: extending their useful life indefinitely while keeping new containers out of production.</p>

<img src="{images[0]}" alt="Glass jars organized for kitchen storage" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Why Glass Beats Plastic</h2>

<p>The statistics on plastic recycling are sobering. According to the OECD (2022), <strong>91% of the world's plastic waste is NOT recycled</strong>. Of all plastic waste generated from 1950-2015, only 9% was recycled, 12% incinerated, and a staggering 79% accumulated in landfills or the natural environment.</p>

<p>Meanwhile, the U.S. has a plastic recycling rate of just <strong>5%</strong>—the worst of all developed countries according to Greenpeace (2022). Glass offers a sustainable alternative that can be reused countless times before recycling.</p>

<blockquote>
<p>"If a glass bottle ends up in the landfill, it could take up to one million years to degrade."</p>
<footer>— <cite>Seattle Post-Intelligencer</cite></footer>
</blockquote>

<img src="{images[1]}" alt="Collection of upcycled glass jars" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Preparing Jars for Reuse</h2>

<h3>Step 1: Remove Labels</h3>

<p>As one crafty community member shares, "I just soak the labels off and re-label them." Here's the process:</p>

<ol>
<li><strong>Soak in warm water:</strong> Submerge jars in warm, soapy water for 30 minutes</li>
<li><strong>Peel labels:</strong> Most slide right off after soaking</li>
<li><strong>Remove residue:</strong> Use baking soda paste, coconut oil, or commercial adhesive removers for stubborn glue</li>
<li><strong>Wash and dry:</strong> Run through dishwasher or hand wash with hot water</li>
</ol>

<h3>Step 2: Remove Odors</h3>

<ul>
<li><strong>Baking soda soak:</strong> Fill with warm water and 2 tablespoons baking soda overnight</li>
<li><strong>Vinegar rinse:</strong> Fill with white vinegar, let sit 30 minutes</li>
<li><strong>Sunlight:</strong> Place open jars in direct sunlight for a few hours</li>
<li><strong>Coffee grounds:</strong> Fill with dry coffee grounds and seal for 24 hours</li>
</ul>

<h2>20+ Creative Uses for Glass Jars</h2>

<img src="{images[2]}" alt="Creative uses for glass jars in home" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h3>Kitchen Organization</h3>

<p>According to <a href="https://thekitchn.com" target="_blank" rel="noopener">The Kitchn</a>, discovering a collection of vintage glass jars is "incredible: Mason jars in every shape and size, ancient spice jars, old-fashioned milk jugs!" Here's how to use them:</p>

<ul>
<li><strong>Dry goods storage:</strong> Pasta, rice, beans, lentils, oats</li>
<li><strong>Spice organization:</strong> Uniform jars create a cohesive look</li>
<li><strong>Baking supplies:</strong> Flour, sugar, baking soda, cocoa powder</li>
<li><strong>Snack containers:</strong> Nuts, dried fruit, granola, crackers</li>
<li><strong>Homemade mixes:</strong> Pancake mix, cookie ingredients, soup starters</li>
</ul>

<div class="tip-box" style="background:#f0f8f0;padding:20px;border-radius:12px;margin:20px 0;border-left:4px solid #4a7c4e;">
<h4>🧂 Salt & Pepper Shakers</h4>
<p>According to <a href="https://upcyclethat.com" target="_blank" rel="noopener">Upcycle That</a>: "Upcycling small mason jars as salt and pepper shakers is a great way to reuse them! Add tiny holes to the lid with a hammer and a nail."</p>
</div>

<h3>Bathroom & Self-Care</h3>

<ul>
<li>Cotton ball and Q-tip storage</li>
<li>Homemade bath salts and scrubs</li>
<li>Makeup brush holders</li>
<li>DIY lotion and cream containers</li>
<li>Hair ties and bobby pin organizers</li>
</ul>

<h3>Home Office & Craft Room</h3>

<ul>
<li>Pencil and pen holders</li>
<li>Button, bead, and notions storage</li>
<li>Paint brush wash containers</li>
<li>Paper clip and push pin organization</li>
<li>Small hardware (screws, nails, bolts)</li>
</ul>

<h3>Gift-Giving Ideas</h3>

<p>As <a href="https://thriftynorthwestmom.com" target="_blank" rel="noopener">Thrifty Northwest Mom</a> shares: "These are 6 of my favorite ways to get glass jars that I can use to organize items, make gifts in, or use as decor in my home for FREE!" Gift ideas include:</p>

<ul>
<li>Layered cookie or soup mix</li>
<li>Homemade candles</li>
<li>Bath salt blends</li>
<li>Hot cocoa kits</li>
<li>Herb and spice blends</li>
<li>Preserved jams and pickles</li>
</ul>

<h3>Garden & Outdoor</h3>

<ul>
<li>Seed starting containers (add drainage holes)</li>
<li>Herb propagation stations</li>
<li>Outdoor citronella candle holders</li>
<li>Small tool organization in shed</li>
<li>Collected rainwater samples</li>
</ul>

<img src="{images[3]}" alt="Decorative upcycled glass jars" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Matching Jar Sizes to Uses</h2>

<table style="width:100%;border-collapse:collapse;margin:20px 0;">
<thead>
<tr style="background:#f8f9fa;">
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Jar Type</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Original Use</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Upcycled Ideas</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding:12px;border:1px solid #ddd;">Baby food jars</td>
<td style="padding:12px;border:1px solid #ddd;">Purees</td>
<td style="padding:12px;border:1px solid #ddd;">Spices, paint storage, travel containers</td>
</tr>
<tr style="background:#f8f9fa;">
<td style="padding:12px;border:1px solid #ddd;">Pasta sauce jars</td>
<td style="padding:12px;border:1px solid #ddd;">Marinara</td>
<td style="padding:12px;border:1px solid #ddd;">Dry goods, flowers, utensil holders</td>
</tr>
<tr>
<td style="padding:12px;border:1px solid #ddd;">Pickle jars</td>
<td style="padding:12px;border:1px solid #ddd;">Pickles</td>
<td style="padding:12px;border:1px solid #ddd;">Bulk storage, fermentation, flour/sugar</td>
</tr>
<tr style="background:#f8f9fa;">
<td style="padding:12px;border:1px solid #ddd;">Jam/jelly jars</td>
<td style="padding:12px;border:1px solid #ddd;">Preserves</td>
<td style="padding:12px;border:1px solid #ddd;">Drinking glasses, overnight oats, gifts</td>
</tr>
<tr>
<td style="padding:12px;border:1px solid #ddd;">Olive jars</td>
<td style="padding:12px;border:1px solid #ddd;">Olives</td>
<td style="padding:12px;border:1px solid #ddd;">Nuts, candy, cotton balls, office supplies</td>
</tr>
</tbody>
</table>

<h2>The Bigger Picture</h2>

<p>According to RTS Waste Solutions, consumers are actively shifting toward sustainability: "Consumers are shifting to eco-friendly and virtue-based brands—evident by the likes of sustainably sourced goods, plant based foods, and repurposed products."</p>

<p>Each American generates <strong>4.9 pounds of waste per day</strong>, and it's growing each year. By upcycling glass jars, you're practicing the most impactful of the three R's: <strong>Reduce</strong>. You're reducing the demand for new containers, reducing what goes to recycling plants, and reducing your household waste.</p>

<blockquote>
<p>"The trade-off between sustainability and profitability no longer exists. Sustainable business practices are emerging as market leaders adopt criteria such as ESG."</p>
<footer>— <cite>RTS Environmental Research</cite></footer>
</blockquote>

<h2>Start Your Jar Collection</h2>

<p>Begin by saving just one type of jar—perhaps pasta sauce jars or pickle jars—and watch as they transform your pantry organization. Once you experience the satisfaction of a zero-cost, zero-waste storage system, you'll find yourself reaching for glass containers instinctively.</p>

<p><em>Looking to complement your upcycled collection? Explore our <a href="/collections/storage">eco-friendly storage solutions</a> designed with the same sustainability principles in mind.</em></p>

</article>
"""

    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

    article_data = {
        "article": {
            "title": "Upcycling Glass Jars for Storage: 20+ Creative Zero-Waste Ideas",
            "author": "The Rike",
            "body_html": html_content,
            "tags": "upcycling,glass-jars,zero-waste,organization,sustainable-living,diy-storage,reduce-reuse-recycle",
            "published": True,
            "image": {
                "src": images[0],
                "alt": "Glass jars organized for kitchen storage",
            },
        }
    }

    resp = requests.post(
        f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json",
        headers=headers,
        json=article_data,
    )

    if resp.status_code == 201:
        article = resp.json()["article"]
        print(f"✅ Article published!")
        print(f"   ID: {article['id']}")
        print(f"   Title: {article['title']}")
        print(f"   URL: https://{SHOP}/blogs/sustainable-living/{article['handle']}")

        seo_title = (
            "Upcycling Glass Jars for Storage | 20+ Creative Reuse Ideas | The Rike"
        )
        seo_desc = "Transform empty glass jars into organized storage. 20+ zero-waste ideas for kitchen, bathroom, office. Save money while reducing waste."

        metafield_data = {
            "metafield": {
                "namespace": "global",
                "key": "title_tag",
                "value": seo_title,
                "type": "single_line_text_field",
            }
        }
        requests.post(
            f"https://{SHOP}/admin/api/2025-01/articles/{article['id']}/metafields.json",
            headers=headers,
            json=metafield_data,
        )

        metafield_data["metafield"]["key"] = "description_tag"
        metafield_data["metafield"]["value"] = seo_desc
        requests.post(
            f"https://{SHOP}/admin/api/2025-01/articles/{article['id']}/metafields.json",
            headers=headers,
            json=metafield_data,
        )

        print(f"   SEO metafields set!")
        return article["id"]
    else:
        print(f"❌ Failed: {resp.status_code}")
        print(resp.text)
        return None


if __name__ == "__main__":
    create_article()
