#!/usr/bin/env python3
"""
Topic 21: DIY Beeswax Wraps for Food Storage - REPUBLISH
With proper hidden links: <a href="url">Source Name</a>
"""

import requests
import json

# === CONFIGURATION ===
SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"
PEXELS_API_KEY = "os.environ.get("PEXELS_API_KEY", "")"


def get_pexels_images(queries, per_query=1):
    """Fetch images from Pexels API"""
    images = []
    headers = {"Authorization": PEXELS_API_KEY}

    for query in queries:
        try:
            resp = requests.get(
                f"https://api.pexels.com/v1/search?query={query}&per_page={per_query}",
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                for photo in data.get("photos", []):
                    images.append(
                        {
                            "url": photo["src"]["large"],
                            "alt": photo.get("alt", query),
                            "photographer": photo.get("photographer", "Unknown"),
                        }
                    )
        except Exception as e:
            print(f"Error fetching image for '{query}': {e}")

    return images


def get_headers():
    return {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}


def find_article_by_title(keyword):
    """Find article by title keyword"""
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json?limit=250"
    resp = requests.get(url, headers=get_headers(), timeout=30)
    if resp.status_code == 200:
        articles = resp.json().get("articles", [])
        for article in articles:
            if keyword.lower() in article["title"].lower():
                return article["id"]
    return None


def update_article(article_id, body_html):
    """Update article with new content"""
    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"

    data = {"article": {"id": article_id, "body_html": body_html}}

    resp = requests.put(url, headers=get_headers(), json=data, timeout=30)
    return resp.status_code == 200


def main():
    # Find article
    print("Finding article: DIY Beeswax Wraps...")
    article_id = find_article_by_title("beeswax wraps")

    if not article_id:
        print("❌ Article not found!")
        return

    print(f"Found article ID: {article_id}")

    # Get images
    image_queries = [
        "beeswax wrap food storage",
        "eco friendly kitchen sustainable",
        "DIY crafts handmade",
        "fresh vegetables fruits wrapped",
    ]
    images = get_pexels_images(image_queries)

    while len(images) < 4:
        images.append(
            {
                "url": "https://images.pexels.com/photos/4498136/pexels-photo-4498136.jpeg",
                "alt": "Eco-friendly food storage",
                "photographer": "Pexels",
            }
        )

    # Article content with PROPER hidden links
    article_html = f"""
<div class="blog-post-content">
    <img src="{images[0]['url']}" alt="{images[0]['alt']}" style="width:100%; max-width:800px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[0]['photographer']}</em></p>

    <p>Every year, billions of feet of plastic wrap end up in landfills, where they'll persist for centuries. According to <a href="https://www.databridgemarketresearch.com/reports/global-plastic-wrap-market" target="_blank" rel="noopener">Data Bridge Market Research</a>, the <strong>global plastic wrap market is valued at $12.13 billion in 2024</strong> and is expected to reach $16.35 billion by 2032. But there's a sustainable alternative that's been used for centuries: beeswax wraps.</p>

    <h2>What Are Beeswax Wraps?</h2>

    <p>According to <a href="https://ucanr.edu/blog/preservation-notes-san-joaquin-master-food-preservers/article/beeswax-food-wraps-possible" target="_blank" rel="noopener">UC Agriculture and Natural Resources</a>, "Beeswax cloth presents a sustainable and eco-friendly alternative to plastic film wraps. Unlike plastic wraps, which contribute to pollution and take years to decompose, beeswax wraps break down naturally, reducing the environmental impact."</p>

    <p>Beeswax wraps are pieces of cotton fabric infused with beeswax, pine resin, and jojoba oil. The warmth of your hands softens the wrap, allowing it to mold around bowls, fruits, vegetables, and sandwiches. Once cooled, it holds its shape, creating a breathable seal that keeps food fresh.</p>

    <h2>Why Make Your Own?</h2>

    <ul>
        <li><strong>Cost savings:</strong> Commercial wraps can cost $15-20 for a pack of three. DIY wraps cost a fraction</li>
        <li><strong>Customization:</strong> Choose your own fabric patterns and sizes</li>
        <li><strong>Quality control:</strong> Know exactly what ingredients go into your wraps</li>
        <li><strong>Fun project:</strong> Great for crafting with kids or as handmade gifts</li>
    </ul>

    <img src="{images[1]['url']}" alt="{images[1]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[1]['photographer']}</em></p>

    <h2>Environmental Benefits</h2>

    <p>According to <a href="https://southernsustainabilityinstitute.org/beeswax-food-wraps-the-eco-friendly-alternative-to-plastic-wrap/" target="_blank" rel="noopener">Southern Sustainability Institute</a>, beeswax wraps offer three key environmental benefits:</p>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Benefit</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Details</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Reduces Plastic Waste</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Each wrap replaces hundreds of feet of plastic wrap over its lifetime</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Compostable & Biodegradable</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">When worn out, wraps can go directly into your compost pile</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Made from Renewable Resources</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Beeswax, cotton, plant oils, and tree resin are all sustainable materials</td>
        </tr>
    </table>

    <h2>The Best Recipe: Beeswax + Pine Resin + Jojoba Oil</h2>

    <p>According to <a href="https://kinshiphandwork.com/making/recipe-for-beeswax-wraps/" target="_blank" rel="noopener">Kinship Handwork</a>, the ideal ratio is:</p>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>The 2:2:1 Ratio</strong>
        <ul>
            <li><strong>2 parts Beeswax</strong> (2/3 cup) - provides the main coating</li>
            <li><strong>2 parts Pine Resin</strong> (2/3 cup) - creates stickiness so wraps seal</li>
            <li><strong>1 part Jojoba Oil</strong> (1/3 cup) - keeps the wrap pliable</li>
        </ul>
        <p><em>This amount makes 7-8 medium wraps.</em></p>
    </div>

    <p>As <a href="https://www.chefsouschef.com/beeswax-wraps/" target="_blank" rel="noopener">Chef Sous Chef</a> notes, "After a couple of craft days testing different ratios, we found the perfect combination of beeswax, pine resin, and jojoba oil for the most effective food wraps."</p>

    <h2>What You'll Need</h2>

    <h3>Ingredients</h3>
    <ul>
        <li>Beeswax pellets or grated beeswax (food-grade)</li>
        <li>Pine resin (also called rosin or colophony)</li>
        <li>Jojoba oil (or coconut oil as alternative)</li>
    </ul>

    <h3>Equipment</h3>
    <ul>
        <li>100% cotton fabric (prewashed)</li>
        <li>Pinking shears or sharp scissors</li>
        <li>Baking sheets lined with parchment paper</li>
        <li>Old paintbrush (dedicated for this purpose)</li>
        <li>Double boiler or glass jar in saucepan</li>
        <li>Oven</li>
        <li>Clothesline and clips for drying</li>
    </ul>

    <img src="{images[2]['url']}" alt="{images[2]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[2]['photographer']}</em></p>

    <h2>Step-by-Step Instructions</h2>

    <ol>
        <li><strong>Prepare fabric:</strong> Wash and dry cotton fabric. Cut into desired sizes using pinking shears (the zigzag edge prevents fraying)</li>
        <li><strong>Preheat oven:</strong> Set to 200°F (93°C)</li>
        <li><strong>Melt ingredients:</strong> Combine beeswax, pine resin, and jojoba oil in a double boiler. Stir until fully melted and combined</li>
        <li><strong>Arrange fabric:</strong> Place fabric pieces on parchment-lined baking sheets</li>
        <li><strong>Apply mixture:</strong> Brush melted mixture evenly across fabric, covering all areas</li>
        <li><strong>Heat in oven:</strong> Place in oven for 2-3 minutes until mixture spreads evenly</li>
        <li><strong>Brush again:</strong> Remove and quickly brush to distribute any pooled wax</li>
        <li><strong>Hang to cool:</strong> Use clips to hang wraps on a clothesline. They'll dry in seconds</li>
    </ol>

    <h2>Recommended Wrap Sizes</h2>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Size</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Dimensions</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Best Uses</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Small</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">7" x 8"</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Lemon halves, small jars, snacks</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Medium</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">10" x 11"</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Sandwiches, avocados, cheese, small bowls</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Large</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">13" x 14"</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Large bowls, bread, celery bunches</td>
        </tr>
    </table>

    <h2>What to Use Beeswax Wraps For</h2>

    <ul>
        <li>Covering bowls of leftovers</li>
        <li>Wrapping cheese, bread, and baked goods</li>
        <li>Storing cut fruits and vegetables</li>
        <li>Wrapping sandwiches and snacks</li>
        <li>Covering rising bread dough</li>
    </ul>

    <h3>What NOT to Use Them For</h3>
    <p>According to UC Agriculture and Natural Resources, "Beeswax wraps are not recommended for use with raw meat or hot items, as the heat can melt the wax coating." Avoid:</p>
    <ul>
        <li>Raw meat, poultry, or fish</li>
        <li>Hot foods (wait until they cool)</li>
        <li>Microwave use</li>
        <li>Acidic foods for extended periods</li>
    </ul>

    <img src="{images[3]['url']}" alt="{images[3]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[3]['photographer']}</em></p>

    <h2>Care and Maintenance</h2>

    <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>Cleaning:</strong>
        <ul>
            <li>Wash in cool water with mild dish soap</li>
            <li>Never use hot water (it will melt the wax)</li>
            <li>Air dry on a dish rack or hang</li>
            <li>Fold and store in a drawer when dry</li>
        </ul>
        <strong>Refreshing:</strong>
        <p>According to <a href="https://blog.mountainroseherbs.com/the-complete-guide-to-diy-beeswax-wraps-including-a-beeless-vegan-food-wrap" target="_blank" rel="noopener">Mountain Rose Herbs</a>, "To refresh, simply pop them back in the oven, remove, and brush a light coat of the melted resin, wax, and oil mixture evenly over the cloth."</p>
    </div>

    <h2>Vegan Alternative</h2>

    <p>According to Chef Sous Chef, "Soy wax works great to make the wraps vegan and can be used at the same ratio as beeswax." You can also use candelilla wax or carnauba wax as vegan alternatives.</p>

    <h2>How Long Do They Last?</h2>

    <p>With proper care, beeswax wraps last 1-2 years with regular use. Signs it's time to replace or refresh:</p>
    <ul>
        <li>Wrap no longer sticks to itself</li>
        <li>Coating looks thin or patchy</li>
        <li>Fabric feels stiff instead of pliable</li>
    </ul>
    <p>When they're finally worn out, cut them into strips for fire starters or add to your compost pile!</p>

    <h2>Final Thoughts</h2>

    <p>Making your own beeswax wraps is a satisfying project that reduces plastic waste, saves money, and creates beautiful, functional tools for your kitchen. With a $12.13 billion plastic wrap industry contributing to our waste problem, every reusable wrap makes a difference. Start with a simple batch, experiment with fabric patterns, and enjoy the sustainable satisfaction of wrapping your leftovers the old-fashioned way.</p>
</div>
"""

    # Update article
    print("Updating article...")
    if update_article(article_id, article_html):
        print(f"✅ SUCCESS! Article updated with proper hidden links!")
    else:
        print("❌ Failed to update article")


if __name__ == "__main__":
    main()
