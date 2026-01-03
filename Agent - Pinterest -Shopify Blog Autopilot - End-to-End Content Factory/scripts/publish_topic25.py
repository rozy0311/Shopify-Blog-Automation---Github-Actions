#!/usr/bin/env python3
"""
Topic 25: Preserving Lemons and Citrus
Published with REAL RESEARCH from web search
"""

import requests
import json
import random

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

    # Get images
    images = get_pexels_images("preserved lemons jar citrus salt", 4)
    if len(images) < 4:
        images += get_pexels_images("lemon jar fermented", 4 - len(images))

    # Default images if API fails
    default_images = [
        "https://images.pexels.com/photos/1414651/pexels-photo-1414651.jpeg",
        "https://images.pexels.com/photos/1414110/pexels-photo-1414110.jpeg",
        "https://images.pexels.com/photos/4021999/pexels-photo-4021999.jpeg",
        "https://images.pexels.com/photos/3872411/pexels-photo-3872411.jpeg",
    ]
    images = images if len(images) >= 4 else default_images

    # Article content with REAL RESEARCH
    html_content = f"""
<article class="blog-article preserving-lemons">

<p class="intro"><strong>The ancient art of preserving lemons transforms ordinary citrus into an extraordinary culinary treasure.</strong> With global lemon and lime production reaching <strong>10.1 million tons in 2023/24</strong> according to the USDA Foreign Agricultural Service, there's never been more abundance—or more opportunity to capture that brightness for year-round enjoyment. This traditional Moroccan technique requires just two ingredients: lemons and sea salt.</p>

<img src="{images[0]}" alt="Preserved lemons in glass jar with salt" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>The Magic of Salt Preservation</h2>

<p>Preserved lemons, known as <em>l'hamd marakad</em> in Morocco, represent one of the most elegant preservation methods ever developed. According to <a href="https://tasteofmaroc.com" target="_blank" rel="noopener">Taste of Maroc</a>, "Two simple ingredients and a few minutes of your time are all that's needed to make homemade preserved lemons." The transformation that occurs over four weeks creates flavors impossible to replicate with fresh citrus.</p>

<p>As noted by <a href="https://cultured.guru" target="_blank" rel="noopener">Cultured Guru</a>, "You only need two ingredients, lemons and sea salt. This recipe takes about 10 minutes to prep and four weeks of fermentation time." This lacto-fermentation process not only preserves but also develops complex, umami-rich flavors.</p>

<blockquote>
<p>"Every year I make preserved lemons and for the first three or four months they are delicious. I always sterilize the jars, use Meyer lemons, use a lot of salt and fill the juice up to the top."</p>
<footer>— Christine, <cite>Taste of Maroc community member</cite></footer>
</blockquote>

<img src="{images[1]}" alt="Fresh lemons ready for preservation" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Step-by-Step Preservation Method</h2>

<h3>Classic Moroccan Technique</h3>

<p>According to <a href="https://toriavey.com" target="_blank" rel="noopener">Tori Avey's tutorial</a>, the traditional method involves:</p>

<ol>
<li><strong>Prepare lemons:</strong> Wash thoroughly, then quarter each lemon from the top, stopping about 1 inch from the bottom so quarters remain attached</li>
<li><strong>Salt generously:</strong> Pack coarse sea salt into the cuts—approximately 1-2 tablespoons per lemon</li>
<li><strong>Layer in jar:</strong> Pour ½ tablespoon salt into jar bottom, place salted lemons, press firmly to release juice</li>
<li><strong>Submerge completely:</strong> Add fresh lemon juice if needed to cover lemons entirely</li>
<li><strong>Cure for 4 weeks:</strong> Shake jar daily for first week, then let rest in cool, dark place</li>
</ol>

<h3>Meyer Lemon Variation</h3>

<p>Meyer lemons, sweeter and less acidic than Eureka varieties, create particularly silky preserved lemons. Their thinner skin becomes meltingly tender during the fermentation process.</p>

<div class="tip-box" style="background:#f0f8f0;padding:20px;border-radius:12px;margin:20px 0;border-left:4px solid #4a7c4e;">
<h4>🍋 Pro Tip: Adding Aromatics</h4>
<p>Enhance your preserved lemons with whole spices: bay leaves, cinnamon sticks, coriander seeds, cloves, or dried chilies create unique flavor profiles for different cuisines.</p>
</div>

<img src="{images[2]}" alt="Lemon preservation process with salt" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Beyond Lemons: Preserving All Citrus</h2>

<p>According to the <a href="https://www.fao.org" target="_blank" rel="noopener">Food and Agriculture Organization</a>, present world production of citrus is about <strong>98.7 million tons</strong> of fresh fruit, of which 62% is orange, 17% mandarin, and 5% citron. This abundance means endless preservation possibilities:</p>

<table style="width:100%;border-collapse:collapse;margin:20px 0;">
<thead>
<tr style="background:#f8f9fa;">
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Citrus Type</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Salt Ratio</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Cure Time</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Best Uses</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding:12px;border:1px solid #ddd;">Lemons</td>
<td style="padding:12px;border:1px solid #ddd;">1-2 tbsp per fruit</td>
<td style="padding:12px;border:1px solid #ddd;">4+ weeks</td>
<td style="padding:12px;border:1px solid #ddd;">Tagines, salads, marinades</td>
</tr>
<tr style="background:#f8f9fa;">
<td style="padding:12px;border:1px solid #ddd;">Limes</td>
<td style="padding:12px;border:1px solid #ddd;">1 tbsp per fruit</td>
<td style="padding:12px;border:1px solid #ddd;">3-4 weeks</td>
<td style="padding:12px;border:1px solid #ddd;">Southeast Asian dishes</td>
</tr>
<tr>
<td style="padding:12px;border:1px solid #ddd;">Oranges</td>
<td style="padding:12px;border:1px solid #ddd;">2 tbsp per fruit</td>
<td style="padding:12px;border:1px solid #ddd;">5-6 weeks</td>
<td style="padding:12px;border:1px solid #ddd;">Duck, pork, desserts</td>
</tr>
<tr style="background:#f8f9fa;">
<td style="padding:12px;border:1px solid #ddd;">Grapefruit</td>
<td style="padding:12px;border:1px solid #ddd;">2 tbsp per fruit</td>
<td style="padding:12px;border:1px solid #ddd;">6-8 weeks</td>
<td style="padding:12px;border:1px solid #ddd;">Seafood, cocktails</td>
</tr>
</tbody>
</table>

<h2>Reducing Citrus Waste Through Preservation</h2>

<p>Research published in <a href="https://www.mdpi.com" target="_blank" rel="noopener">MDPI journals (Allegra, 2025)</a> highlights that preservation methods "save time, reduce food waste, and provide standardized quality." By preserving seasonal citrus bounty, home cooks can enjoy peak-ripeness flavor months later while eliminating waste from forgotten produce.</p>

<p>According to food preservation research, citrus peels contain valuable phenolic compounds and carotenoids that are preserved through salt-curing—compounds that help extend shelf life naturally.</p>

<blockquote>
<p>"Citrus waste, which is a rich source of phenolic compounds and carotenoids, helps to extend the shelf life of food naturally."</p>
<footer>— Food Technology and Biotechnology journal</footer>
</blockquote>

<img src="{images[3]}" alt="Various preserved citrus varieties" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Using Your Preserved Citrus</h2>

<h3>In the Kitchen</h3>

<ul>
<li><strong>Tagines and stews:</strong> The classic application—sliced rind adds depth to Moroccan cuisine</li>
<li><strong>Salad dressings:</strong> Finely chopped preserved lemon transforms vinaigrettes</li>
<li><strong>Roasted vegetables:</strong> Toss with olive oil and preserved citrus for caramelized brightness</li>
<li><strong>Grain bowls:</strong> Adds sophisticated umami to simple grains</li>
<li><strong>Compound butter:</strong> Blend into softened butter for finishing fish or vegetables</li>
</ul>

<h3>Pro Technique: Using the Brine</h3>

<p>Don't discard the brine! This concentrated liquid gold works beautifully in:</p>
<ul>
<li>Cocktails (especially martinis and Bloody Marys)</li>
<li>Marinades for chicken or fish</li>
<li>Salad dressings in place of vinegar</li>
<li>Pickling other vegetables</li>
</ul>

<h2>Storage and Shelf Life</h2>

<div class="info-box" style="background:#e8f4f8;padding:20px;border-radius:12px;margin:20px 0;">
<h4>📦 Proper Storage Ensures Longevity</h4>
<ul>
<li><strong>Refrigerated:</strong> 1 year or longer once fully cured</li>
<li><strong>Room temperature (during curing):</strong> Keep in cool, dark place</li>
<li><strong>Always submerged:</strong> Lemons above brine line may develop mold</li>
<li><strong>Clean utensils:</strong> Use clean fork or spoon to remove lemons</li>
</ul>
</div>

<h2>Start Your Preservation Journey</h2>

<p>With just lemons, salt, and patience, you'll create a pantry staple that elevates everything from weeknight dinners to special occasions. The minimal effort required—perhaps 10 minutes of prep—yields months of culinary possibilities. Begin with a single jar, and you'll soon find preserved lemons indispensable in your sustainable kitchen.</p>

<p><em>Ready to explore more traditional preservation techniques? Discover how our <a href="/collections/food-storage">reusable food storage solutions</a> complement your preserved pantry, keeping your culinary creations fresh and organized.</em></p>

</article>
"""

    # Create article via Shopify API
    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

    article_data = {
        "article": {
            "title": "Preserving Lemons and Citrus: The Ancient Art of Salt-Cured Flavor",
            "author": "The Rike",
            "body_html": html_content,
            "tags": "preservation,lemons,citrus,fermentation,zero-waste,moroccan-cooking,sustainable-kitchen,food-storage",
            "published": True,
            "image": {
                "src": images[0],
                "alt": "Preserved lemons in glass jar with sea salt",
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

        # Set SEO metafields
        seo_title = (
            "How to Preserve Lemons & Citrus | Salt Preservation Guide | The Rike"
        )
        seo_desc = "Master the ancient Moroccan art of preserving lemons with salt. 10-minute prep, 4-week cure for year-round citrus flavor. Step-by-step guide with tips."

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
