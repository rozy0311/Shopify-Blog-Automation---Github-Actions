#!/usr/bin/env python3
"""
Topic 26: Making Fruit Leather at Home
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

    # Get images
    images = get_pexels_images("fruit snack dried berries healthy", 4)
    if len(images) < 4:
        images += get_pexels_images("fresh fruit blender puree", 4 - len(images))

    default_images = [
        "https://images.pexels.com/photos/1132047/pexels-photo-1132047.jpeg",
        "https://images.pexels.com/photos/1300972/pexels-photo-1300972.jpeg",
        "https://images.pexels.com/photos/1028599/pexels-photo-1028599.jpeg",
        "https://images.pexels.com/photos/5945755/pexels-photo-5945755.jpeg",
    ]
    images = images if len(images) >= 4 else default_images

    html_content = f"""
<article class="blog-article fruit-leather">

<p class="intro"><strong>Homemade fruit leather transforms seasonal abundance into portable, healthy snacks that outshine any store-bought version.</strong> With the global fruit snacks market projected to reach <strong>$48.60 billion by 2035</strong> according to market research, consumers are increasingly seeking healthier alternatives to processed confections. The solution? Making your own fruit leather requires just fruit, patience, and basic kitchen equipment.</p>

<img src="{images[0]}" alt="Homemade fruit leather rolls with fresh fruit" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Why Make Fruit Leather at Home?</h2>

<p>According to <a href="https://mordorintelligence.com" target="_blank" rel="noopener">Mordor Intelligence</a>, conventional fruit snacks maintain <strong>85.67% market share in 2024</strong>, yet organic variants are accelerating at <strong>10.55% CAGR through 2030</strong>—indicating growing demand for healthier, additive-free options. Homemade fruit leather offers the ultimate control over ingredients: pure fruit with no added sugars, preservatives, or artificial colors.</p>

<p>As <a href="https://instructables.com" target="_blank" rel="noopener">Instructables creator Paige Russell</a> shares: "Fruit leather is one of my favorite dried snacks. And PEAR fruit leather is at the top of my leather favorites pyramid."</p>

<blockquote>
<p>"Fruit leather or homemade fruit roll ups are a tasty snack that my family loves. It's basically pureed fruit that's dried in a thin layer that can be rolled up for perfect sized snacks to go."</p>
<footer>— Getty Stewart, <cite>Professional Home Economist</cite></footer>
</blockquote>

<img src="{images[1]}" alt="Fresh fruits ready for making leather" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Choosing the Right Fruits</h2>

<p>According to <a href="https://gettystewart.com" target="_blank" rel="noopener">Getty Stewart's comprehensive guide</a>, there are endless fruit options for making leather. Here are the best categories:</p>

<h3>Best Fruits for Leather</h3>

<ul>
<li><strong>Berries:</strong> Strawberries, blueberries, raspberries, blackberries</li>
<li><strong>Stone fruits:</strong> Apricots, plums, peaches, cherries, chokecherries</li>
<li><strong>Tropical fruits:</strong> Mangos, pineapple, papaya</li>
<li><strong>Others:</strong> Apples, pears, applesauce, cranberry sauce, pumpkin or squash puree</li>
</ul>

<div class="tip-box" style="background:#fff3cd;padding:20px;border-radius:12px;margin:20px 0;border-left:4px solid #ffc107;">
<h4>💡 Pro Tip: The Pectin Secret</h4>
<p>Getty Stewart advises: "Fruit naturally high in pectin (apples, plums, citrus, currants, cranberries) will ensure the leather bonds well and makes a nice, crack-free leather. That's why many recipes often include an apple or applesauce in the recipe."</p>
</div>

<h3>Fruits to Combine</h3>

<p>Some fruits work better when combined with drier fruits:</p>
<ul>
<li><strong>High water content fruits</strong> (melons, citrus, kiwi, grapes) take longer to dry—combine with drier fruits</li>
<li><strong>Bananas</strong> are high in starch and don't work well alone—use a small ratio combined with other fruit</li>
<li><strong>Seeded berries</strong> (raspberries, blackberries) can be strained for smoother texture</li>
</ul>

<img src="{images[2]}" alt="Fruit puree being spread for dehydrating" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Two Methods: Dehydrator vs. Oven</h2>

<h3>Method 1: Using a Dehydrator</h3>

<p>According to Getty Stewart's detailed instructions:</p>

<ol>
<li><strong>Prepare trays:</strong> Line dehydrator with paraflexx sheet, parchment paper, silpat, or plastic wrap. <em>NEVER use wax paper!</em></li>
<li><strong>Spread evenly:</strong> Pour fruit puree ⅛ to ¼ inch (2-5mm) thick. Use an offset spatula for even layers</li>
<li><strong>Dehydrate:</strong> Set to 135°F (57°C) for 6-8 hours (longer in humid conditions)</li>
<li><strong>Check dryness:</strong> Press with flat fingers—if there's an indentation or wet spots, it's not ready</li>
<li><strong>Cool and roll:</strong> Let cool completely, then roll and cut into strips</li>
</ol>

<table style="width:100%;border-collapse:collapse;margin:20px 0;">
<thead>
<tr style="background:#f8f9fa;">
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Fruit Type</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Puree Amount</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Drying Time</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Tips</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding:12px;border:1px solid #ddd;">Berries</td>
<td style="padding:12px;border:1px solid #ddd;">2-3 cups/tray</td>
<td style="padding:12px;border:1px solid #ddd;">6-8 hours</td>
<td style="padding:12px;border:1px solid #ddd;">Strain seeds if desired</td>
</tr>
<tr style="background:#f8f9fa;">
<td style="padding:12px;border:1px solid #ddd;">Stone Fruits</td>
<td style="padding:12px;border:1px solid #ddd;">2-3 cups/tray</td>
<td style="padding:12px;border:1px solid #ddd;">8-10 hours</td>
<td style="padding:12px;border:1px solid #ddd;">Add apple for binding</td>
</tr>
<tr>
<td style="padding:12px;border:1px solid #ddd;">Tropical</td>
<td style="padding:12px;border:1px solid #ddd;">2-3 cups/tray</td>
<td style="padding:12px;border:1px solid #ddd;">8-12 hours</td>
<td style="padding:12px;border:1px solid #ddd;">Higher moisture content</td>
</tr>
<tr style="background:#f8f9fa;">
<td style="padding:12px;border:1px solid #ddd;">Applesauce</td>
<td style="padding:12px;border:1px solid #ddd;">2-3 cups/tray</td>
<td style="padding:12px;border:1px solid #ddd;">6-7 hours</td>
<td style="padding:12px;border:1px solid #ddd;">Naturally high pectin</td>
</tr>
</tbody>
</table>

<h3>Method 2: Using Your Oven</h3>

<p>No dehydrator? No problem! Getty Stewart provides oven instructions:</p>

<ol>
<li><strong>Preheat oven:</strong> Set to 170°F (80°C). Line rimmed baking sheet with parchment paper</li>
<li><strong>Spread puree:</strong> 3-4 cups per 11×17 inch baking sheet, ⅛ to ¼ inch thick</li>
<li><strong>Bake 6-8 hours:</strong> Until no longer sticky, no wet spots visible</li>
<li><strong>Test doneness:</strong> Should not leave indentations when pressed, separates easily from parchment</li>
<li><strong>Cool and store:</strong> Roll with parchment paper to prevent sticking</li>
</ol>

<blockquote>
<p>"If you are lucky enough to have a convection setting on your oven, always use that for dehydrating, as the air flow created cuts down the oven drying times by almost half."</p>
<footer>— Paige Russell, <cite>Instructables</cite></footer>
</blockquote>

<img src="{images[3]}" alt="Finished fruit leather being rolled" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Flavor Combinations to Try</h2>

<h3>Classic Favorites</h3>

<ul>
<li><strong>Apple Cinnamon:</strong> Applesauce with cinnamon and nutmeg</li>
<li><strong>Berry Blast:</strong> Mixed strawberries, blueberries, raspberries</li>
<li><strong>Tropical Sunset:</strong> Mango with pineapple</li>
<li><strong>Stone Fruit Medley:</strong> Peaches with apricots</li>
</ul>

<h3>Creative Additions</h3>

<p>Getty Stewart suggests getting creative with add-ins:</p>
<ul>
<li><strong>Spices:</strong> Cinnamon, nutmeg, coriander, allspice, clove, ginger, pumpkin pie spice</li>
<li><strong>Unexpected twist:</strong> Even a hint of hot pepper for adventurous palates!</li>
<li><strong>Leftover magic:</strong> "Leftover cranberry sauce mixed with applesauce makes a tasty, colourful leather"</li>
</ul>

<div class="recipe-box" style="background:#f0f8f0;padding:20px;border-radius:12px;margin:20px 0;border-left:4px solid #4a7c4e;">
<h4>🍐 Pear Leather Recipe (from Paige Russell)</h4>
<ul>
<li>4 cups washed ripe pears (approximately 8 pears)</li>
<li>4 tsp lemon juice (fresh or bottled) OR ¼ tsp ascorbic acid</li>
<li>Optional: cinnamon, lavender, or mint for flavor</li>
</ul>
<p><em>Blend until smooth, spread thin, dehydrate at 135°F for 6-8 hours</em></p>
</div>

<h2>Storage Tips</h2>

<ul>
<li><strong>Room temperature:</strong> 1-2 weeks in airtight container</li>
<li><strong>Refrigerated:</strong> 1-2 months</li>
<li><strong>Frozen:</strong> Up to 1 year</li>
<li><strong>Prevent sticking:</strong> Roll with parchment paper between layers</li>
</ul>

<h2>Reduce Waste, Create Delicious Snacks</h2>

<p>Fruit leather transforms overripe fruit, seasonal surplus, and even leftover cranberry sauce into portable, shelf-stable snacks. With the growing demand for chemical-free, fat-free, and lower-calorie options driving market growth, homemade fruit leather perfectly aligns with the movement toward healthier snacking—without the premium price tag.</p>

<p><em>Ready to elevate your snack game? Discover our <a href="/collections/food-storage">reusable food storage containers</a> perfect for storing your homemade fruit leather creations.</em></p>

</article>
"""

    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

    article_data = {
        "article": {
            "title": "Making Fruit Leather at Home: The Complete Guide to Healthy DIY Snacks",
            "author": "The Rike",
            "body_html": html_content,
            "tags": "fruit-leather,dehydrating,healthy-snacks,zero-waste,preservation,diy-snacks,sustainable-kitchen",
            "published": True,
            "image": {"src": images[0], "alt": "Homemade fruit leather rolls"},
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

        # SEO metafields
        seo_title = (
            "How to Make Fruit Leather at Home | Dehydrator & Oven Guide | The Rike"
        )
        seo_desc = "Complete guide to making homemade fruit leather using a dehydrator or oven. Healthy, zero-waste snacks from fresh fruit. Step-by-step instructions."

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
