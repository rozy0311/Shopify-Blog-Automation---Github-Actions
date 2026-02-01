#!/usr/bin/env python3
"""
Topic 22: Composting in Small Spaces - REPUBLISH
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
    print("Finding article: Composting Small Spaces...")
    article_id = find_article_by_title("composting")

    if not article_id:
        print("❌ Article not found!")
        return

    print(f"Found article ID: {article_id}")

    # Get images
    image_queries = [
        "composting kitchen scraps organic",
        "worm composting vermicomposting bin",
        "apartment balcony garden plants",
        "soil compost rich organic",
    ]
    images = get_pexels_images(image_queries)

    while len(images) < 4:
        images.append(
            {
                "url": "https://images.pexels.com/photos/4505166/pexels-photo-4505166.jpeg",
                "alt": "Composting organic waste",
                "photographer": "Pexels",
            }
        )

    # Article content with PROPER hidden links
    article_html = f"""
<div class="blog-post-content">
    <img src="{images[0]['url']}" alt="{images[0]['alt']}" style="width:100%; max-width:800px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[0]['photographer']}</em></p>

    <p>Living in an apartment doesn't mean you can't compost. According to the <a href="https://www.usda.gov/sites/default/files/documents/NATIONAL-STRATEGY-FOR-REDUCING-FOOD-LOSS-AND-WASTE-AND-RECYCLING-ORGANICS.pdf" target="_blank" rel="noopener">USDA National Strategy for Reducing Food Waste</a>, <strong>food waste is responsible for 58% of landfill methane emissions</strong> released into the atmosphere. By composting at home—even in a tiny apartment—you're making a real difference.</p>

    <h2>Why Compost in Small Spaces?</h2>

    <p>According to <a href="https://extension.illinois.edu/blogs/everyday-environment-blog/2024-10-17-reduce-methane-generation-composting" target="_blank" rel="noopener">University of Illinois Extension</a>, "Nationally, landfills and trash incinerators receive 167 million tons of garbage a year. Half of that is compostable and 21% is food scraps."</p>

    <p>As <a href="https://www.trashbutler.com/composting-benefits-for-apartments/" target="_blank" rel="noopener">Trash Butler</a> explains, "Composting significantly reduces landfill waste, lowers greenhouse gas emissions, and enhances soil health."</p>

    <h3>Benefits of Apartment Composting</h3>
    <ul>
        <li><strong>Reduce garbage output:</strong> Divert up to 30% of household waste from landfills</li>
        <li><strong>Free fertilizer:</strong> Create nutrient-rich soil for houseplants or community gardens</li>
        <li><strong>Lower carbon footprint:</strong> Prevent methane emissions from rotting food in landfills</li>
        <li><strong>Zero waste lifestyle:</strong> Take a meaningful step toward sustainability</li>
    </ul>

    <h2>Best Composting Methods for Small Spaces</h2>

    <p>According to <a href="https://lifestyle.sustainability-directory.com/learn/can-composting-be-done-indoors-and-what-method-is-best-for-small-spaces/" target="_blank" rel="noopener">Sustainability Directory</a>, "Vermicomposting with worms is the best indoor method for small spaces, as it processes food scraps with minimal odor and mess."</p>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Method</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Space Needed</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Best For</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Vermicomposting</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Under sink or closet</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Year-round indoor composting</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Bokashi</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Countertop bucket</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">All food waste including meat/dairy</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Countertop Electric</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Kitchen counter</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Quick processing, minimal effort</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Balcony Tumbler</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Small balcony corner</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Traditional composting with outdoor space</td>
        </tr>
    </table>

    <img src="{images[1]['url']}" alt="{images[1]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[1]['photographer']}</em></p>

    <h2>Method 1: Vermicomposting (Worm Bin)</h2>

    <p>Vermicomposting uses red wiggler worms to break down food scraps into nutrient-rich castings. It's quiet, odorless when done correctly, and fits under a kitchen sink.</p>

    <h3>What You'll Need</h3>
    <ul>
        <li>Two stacking bins with drainage holes</li>
        <li>Red wiggler worms (about 1 lb per person)</li>
        <li>Bedding material (shredded newspaper, cardboard)</li>
        <li>Kitchen scraps</li>
    </ul>

    <h3>How to Set Up</h3>
    <ol>
        <li><strong>Prepare bedding:</strong> Soak shredded newspaper until damp like a wrung-out sponge</li>
        <li><strong>Add bedding to bin:</strong> Fill bottom bin about 3-4 inches deep</li>
        <li><strong>Add worms:</strong> Gently place worms on top of bedding</li>
        <li><strong>Bury food scraps:</strong> Add small amounts of scraps, covered with bedding</li>
        <li><strong>Maintain moisture:</strong> Keep bedding damp but not wet</li>
    </ol>

    <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>✅ Worms Love:</strong> Fruit/veggie scraps, coffee grounds, tea bags, crushed eggshells, shredded paper<br><br>
        <strong>❌ Avoid:</strong> Citrus, onions, garlic, meat, dairy, oily foods, pet waste
    </div>

    <h2>Method 2: Bokashi Composting</h2>

    <p>According to <a href="https://memotherearthbrand.com/blogs/plastic-free-living/composting-in-an-apartment-yes-it-s-totally-doable" target="_blank" rel="noopener">me.motherearth</a>, "Bokashi is a compact, odor-free method that uses special microbes to ferment all food waste—including meat and dairy—without any smell."</p>

    <p>Research from <a href="https://sobokashi.com/scientific-studies-on-the-effectiveness-of-bokashi-composting-what-does-the-research-say/" target="_blank" rel="noopener">SO Bokashi</a> confirms that "by locking in carbon and returning it to the soil, bokashi could contribute to a fertility boost, benefitting plant growth and aiding in carbon sequestration."</p>

    <h3>How Bokashi Works</h3>
    <ol>
        <li><strong>Add food scraps:</strong> Put any food waste in the sealed bucket</li>
        <li><strong>Sprinkle bokashi bran:</strong> Add a handful of inoculated bran on top</li>
        <li><strong>Press down:</strong> Remove air pockets and seal tightly</li>
        <li><strong>Drain liquid:</strong> Drain "bokashi tea" every few days (dilute for plant fertilizer)</li>
        <li><strong>Ferment:</strong> Once full, let ferment 2 weeks</li>
        <li><strong>Bury:</strong> Dig into soil or add to outdoor compost to finish</li>
    </ol>

    <img src="{images[2]['url']}" alt="{images[2]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[2]['photographer']}</em></p>

    <h2>Method 3: Electric Composters</h2>

    <p>Countertop electric composters like Lomi, FoodCycler, or Vitamix FoodCycler process food waste in hours instead of months. They grind and heat scraps to create a dry, odorless soil amendment.</p>

    <h3>Pros and Cons</h3>
    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Pros</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Cons</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;">
                <ul style="margin: 0; padding-left: 20px;">
                    <li>Very fast (4-8 hours)</li>
                    <li>No maintenance</li>
                    <li>Handles all food waste</li>
                    <li>Odor-free</li>
                </ul>
            </td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">
                <ul style="margin: 0; padding-left: 20px;">
                    <li>Expensive ($300-500)</li>
                    <li>Uses electricity</li>
                    <li>Replacement filters needed</li>
                    <li>Output is dried, not true compost</li>
                </ul>
            </td>
        </tr>
    </table>

    <h2>Method 4: Balcony Tumbler</h2>

    <p>If you have even a small balcony, a compact tumbler composter works well. The tumbling action speeds decomposition and keeps pests out.</p>

    <h3>Tips for Balcony Composting</h3>
    <ul>
        <li>Choose a tumbler with 37 gallons or less capacity</li>
        <li>Position in partial shade to prevent overheating</li>
        <li>Add equal parts "greens" (food scraps) and "browns" (dry leaves, cardboard)</li>
        <li>Tumble every few days to aerate</li>
        <li>Expect finished compost in 4-8 weeks</li>
    </ul>

    <h2>What Can You Compost?</h2>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">✅ YES - Compost These</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">❌ NO - Avoid These</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;">
                <ul style="margin: 0; padding-left: 20px;">
                    <li>Fruit & vegetable scraps</li>
                    <li>Coffee grounds & filters</li>
                    <li>Tea bags (remove staples)</li>
                    <li>Eggshells (crushed)</li>
                    <li>Bread and grains</li>
                    <li>Paper towels (unbleached)</li>
                    <li>Houseplant trimmings</li>
                </ul>
            </td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">
                <ul style="margin: 0; padding-left: 20px;">
                    <li>Meat and fish (vermi/traditional)</li>
                    <li>Dairy products (vermi/traditional)</li>
                    <li>Oily or greasy foods</li>
                    <li>Pet waste</li>
                    <li>Diseased plants</li>
                    <li>Treated or glossy paper</li>
                    <li>Plastic-coated items</li>
                </ul>
            </td>
        </tr>
    </table>

    <img src="{images[3]['url']}" alt="{images[3]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[3]['photographer']}</em></p>

    <h2>Troubleshooting Common Issues</h2>

    <h3>Bad Smell</h3>
    <ul>
        <li><strong>Cause:</strong> Too wet, not enough air, or wrong materials</li>
        <li><strong>Fix:</strong> Add dry browns (shredded paper), mix/aerate, avoid meat/dairy</li>
    </ul>

    <h3>Fruit Flies</h3>
    <ul>
        <li><strong>Cause:</strong> Exposed food scraps</li>
        <li><strong>Fix:</strong> Always bury scraps under bedding, add a layer of newspaper on top</li>
    </ul>

    <h3>Too Slow</h3>
    <ul>
        <li><strong>Cause:</strong> Cold temperatures or wrong balance</li>
        <li><strong>Fix:</strong> Chop scraps smaller, maintain 50/50 green to brown ratio</li>
    </ul>

    <h2>What to Do With Your Compost</h2>

    <p>Once your compost is ready (dark, crumbly, earthy-smelling), you can:</p>
    <ul>
        <li>Feed houseplants and container gardens</li>
        <li>Donate to community gardens</li>
        <li>Share with neighbors who garden</li>
        <li>Add to balcony planters</li>
        <li>Use as mulch around trees</li>
    </ul>

    <h2>Final Thoughts</h2>

    <p>According to <a href="https://keepmassbeautiful.org/news-events/the-kmb-blog/overview.html/article/2025/03/14/composting-to-reduce-food-waste-a-sustainable-path-forward" target="_blank" rel="noopener">Keep Mass Beautiful</a>, "Food accounts for 22% of trash. Methane is released as food decomposes, greatly increasing greenhouse gas emissions."</p>

    <p>With 58% of landfill methane coming from food waste, your small apartment composting system makes a real difference. Whether you choose worms, bokashi, or an electric composter, you're taking a meaningful step toward sustainability—right from your kitchen.</p>
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
