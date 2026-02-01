#!/usr/bin/env python3
"""
Topic 28: Homemade Yogurt Without Special Equipment
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

    images = get_pexels_images("homemade yogurt jar healthy", 4)
    if len(images) < 4:
        images += get_pexels_images("yogurt berry breakfast dairy", 4 - len(images))

    default_images = [
        "https://images.pexels.com/photos/414262/pexels-photo-414262.jpeg",
        "https://images.pexels.com/photos/1192025/pexels-photo-1192025.jpeg",
        "https://images.pexels.com/photos/1092730/pexels-photo-1092730.jpeg",
        "https://images.pexels.com/photos/128865/pexels-photo-128865.jpeg",
    ]
    images = images if len(images) >= 4 else default_images

    html_content = f"""
<article class="blog-article homemade-yogurt">

<p class="intro"><strong>Homemade yogurt delivers superior taste, nutrition, and savings—and you don't need any special equipment to make it.</strong> The U.S. yogurt and probiotic drink market was valued at <strong>$8.43 billion in 2022</strong> and is growing at 8.7% annually, according to Grand View Research. Yet the simplest, most nutritious yogurt can be made in your own kitchen with just milk, a starter culture, and a warm spot.</p>

<img src="{images[0]}" alt="Homemade yogurt in glass jars" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>The Science Behind Yogurt</h2>

<p>According to <a href="https://revolutionfermentation.com" target="_blank" rel="noopener">Revolution Fermentation</a>, "Not all yogurts can be labelled as yogurt. In order to qualify, the yogurt starter culture must at least contain the <em>Lactobacillus bulgaricus</em> and <em>Streptococcus thermophilus</em> bacteria types." These thermophilic (heat-loving) bacteria transform milk into yogurt through fermentation.</p>

<p>The critical parameters:</p>
<ul>
<li><strong>Temperature:</strong> 41-45°C (106-113°F) for 4-8 hours</li>
<li><strong>Caution:</strong> Do not exceed 45°C—the beneficial bacteria will die</li>
</ul>

<p>This is why a yogurt maker exists—to maintain consistent temperature. But as we'll explore, you can achieve the same results without one.</p>

<blockquote>
<p>"It turns out that making yogurt in large batches was much easier than I had imagined. Instead of using the yogurt maker, I tried making the yogurt in my oven."</p>
<footer>— Tracy Ariza, DDS, <cite>The Things We'll Make</cite></footer>
</blockquote>

<img src="{images[1]}" alt="Fresh milk and yogurt starter culture" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>5 Methods Without a Yogurt Maker</h2>

<p>As <a href="https://revolutionfermentation.com" target="_blank" rel="noopener">Revolution Fermentation</a> explains, "It is entirely possible to make your own yogurt without a yogurt maker." Here are five proven methods:</p>

<h3>1. The Oven Method (Most Popular)</h3>

<p>According to Tracy Ariza's detailed guide on <a href="https://thethingswellmake.com" target="_blank" rel="noopener">The Things We'll Make</a>:</p>

<ol>
<li><strong>Heat milk:</strong> Use a double boiler to heat milk to 185°F/85°C slowly (prevents curdling)</li>
<li><strong>Cool milk:</strong> Let cool to 110°F/43°C—speed up by placing pot in cold water</li>
<li><strong>Add culture:</strong> Stir in ½ cup yogurt starter per liter of milk</li>
<li><strong>Turn off oven:</strong> But leave the oven light ON (provides gentle heat)</li>
<li><strong>Strain and pour:</strong> Pour into glass jars, straining to remove lumps or skin</li>
<li><strong>Incubate:</strong> Place jars in oven with light on for 7 hours</li>
<li><strong>Refrigerate:</strong> Cool jars, then store in refrigerator</li>
</ol>

<div class="tip-box" style="background:#fff3cd;padding:20px;border-radius:12px;margin:20px 0;border-left:4px solid #ffc107;">
<h4>⚠️ Important Note</h4>
<p>Revolution Fermentation advises: "This will not work with a LED bulb oven!" Also, "Remember to put a note on the door so that no one in the household accidentally turns on the oven!"</p>
</div>

<h3>2. The Cooler Method</h3>

<p>"A small camping cooler is easy to turn into a yogurt incubator. Simply place a few bottles of hot water around the inoculated milk container."</p>

<h3>3. The Thermos Method</h3>

<p>"Quality insulated containers (Thermos style) can keep a liquid at the same temperature for several hours. Simply pour inoculated milk at 42°C into the thermos. Wrap with a towel for extra insulation."</p>

<h3>4. The Dehydrator Method</h3>

<p>"Put the milk from the yogurt culture in well-sealed glass jars and place them in the dehydrator. Set the temperature to 42°C, and you're done!"</p>

<h3>5. The Pressure Cooker Method</h3>

<p>"Pressure cookers, also known as multi-cookers, often have a 'yogurt' mode that maintains a constant temperature during fermentation."</p>

<img src="{images[2]}" alt="Yogurt incubating in oven with light on" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>The Basic Recipe</h2>

<div class="recipe-box" style="background:#f0f8f0;padding:20px;border-radius:12px;margin:20px 0;border-left:4px solid #4a7c4e;">
<h4>🥛 Simple Homemade Yogurt</h4>
<p><strong>Ingredients (per batch):</strong></p>
<ul>
<li>1 liter (4 cups) whole milk</li>
<li>½ cup starter culture (plain full-fat yogurt with live cultures)</li>
</ul>
<p><strong>Equipment:</strong></p>
<ul>
<li>Cooking thermometer</li>
<li>Double boiler or heavy pot</li>
<li>Glass jars for storage</li>
<li>Strainer (optional)</li>
</ul>
</div>

<h2>Why Whole Milk Works Best</h2>

<p>According to Tracy Ariza: "Yogurt made at home with whole milk turns out pretty thick on its own." The natural fats in whole milk contribute to a creamier, more satisfying texture without additives.</p>

<h3>Thickening Options</h3>

<ul>
<li><strong>Strain it:</strong> Use a tight-weave cloth to strain for Greek-style thickness</li>
<li><strong>Add gelatin:</strong> Mix into the milk while heating</li>
<li><strong>Add powdered milk:</strong> Especially helpful with low-fat milk</li>
</ul>

<h2>The Health Benefits</h2>

<p>The global probiotic yogurt market was valued at <strong>$2.5 billion in 2022</strong> and is growing at 6.5% CAGR through 2032, according to GM Insights. This growth is driven by:</p>

<ul>
<li><strong>Gut health awareness:</strong> Probiotics support digestive health and boost immunity</li>
<li><strong>Reduced sugar:</strong> Homemade yogurt contains no added sugars or artificial sweeteners</li>
<li><strong>Living cultures:</strong> Fresh homemade yogurt contains more active probiotics than store-bought</li>
</ul>

<p>According to a 2022 International Food Information Council (IFIC) study, <strong>32% of Americans actively consume probiotics</strong>, with 60% aiming for daily consumption. Homemade yogurt offers the most affordable way to meet this goal.</p>

<blockquote>
<p>"Probiotics are known to promote gut health, boost the immune system, and improve digestion, which aligns with the increasing interest in health and wellness among consumers."</p>
<footer>— <cite>GM Insights Market Analysis</cite></footer>
</blockquote>

<img src="{images[3]}" alt="Yogurt parfait with fresh berries" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>The Self-Perpetuating Cycle</h2>

<p>Tracy Ariza shares the ultimate money-saving tip: "Save some of your homemade yogurt to use as the starter culture of your next batch! (No more buying yogurt at the store!)"</p>

<p>Each batch becomes the starter for the next, creating an endless supply of fresh, probiotic-rich yogurt for just the cost of milk.</p>

<h2>Common Questions</h2>

<table style="width:100%;border-collapse:collapse;margin:20px 0;">
<thead>
<tr style="background:#f8f9fa;">
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Question</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Answer</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding:12px;border:1px solid #ddd;">Why heat milk first?</td>
<td style="padding:12px;border:1px solid #ddd;">Heating to 185°F denatures proteins for better texture</td>
</tr>
<tr style="background:#f8f9fa;">
<td style="padding:12px;border:1px solid #ddd;">How long does it keep?</td>
<td style="padding:12px;border:1px solid #ddd;">2-3 weeks refrigerated</td>
</tr>
<tr>
<td style="padding:12px;border:1px solid #ddd;">Can I use non-dairy milk?</td>
<td style="padding:12px;border:1px solid #ddd;">Yes, but may need additional thickeners</td>
</tr>
<tr style="background:#f8f9fa;">
<td style="padding:12px;border:1px solid #ddd;">Why is my yogurt thin?</td>
<td style="padding:12px;border:1px solid #ddd;">Temperature too low, time too short, or weak starter</td>
</tr>
</tbody>
</table>

<h2>Start Your Yogurt-Making Journey</h2>

<p>With just milk, starter, and a creative heating solution, you can produce superior yogurt at a fraction of store prices. The process takes minutes of active time and rewards you with probiotic-rich, additive-free yogurt that tastes remarkably better than anything from a plastic container.</p>

<p><em>Looking for the perfect containers for your homemade yogurt? Explore our <a href="/collections/food-storage">glass storage jars</a> designed for fermentation and food preservation.</em></p>

</article>
"""

    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

    article_data = {
        "article": {
            "title": "Homemade Yogurt Without Special Equipment: 5 Easy Methods",
            "author": "The Rike",
            "body_html": html_content,
            "tags": "homemade-yogurt,fermentation,probiotics,gut-health,diy-dairy,sustainable-kitchen,healthy-eating",
            "published": True,
            "image": {"src": images[0], "alt": "Homemade yogurt in glass jars"},
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
            "How to Make Homemade Yogurt Without a Yogurt Maker | 5 Easy Methods"
        )
        seo_desc = "Make creamy probiotic yogurt at home without special equipment. Oven, cooler, thermos methods explained. Save money, boost gut health naturally."

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
