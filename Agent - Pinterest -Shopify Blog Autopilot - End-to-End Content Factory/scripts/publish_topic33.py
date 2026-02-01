#!/usr/bin/env python3
"""
Topic 33: Growing Microgreens on Your Windowsill
Research-backed article with real citations, quotes, and statistics
"""

import requests
import json
from datetime import datetime

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


def create_article():
    """Create and publish the article"""

    # Get 4 relevant images
    image_queries = [
        "microgreens growing tray",
        "windowsill herbs plants",
        "sprouting seeds gardening",
        "healthy green salad fresh",
    ]
    images = get_pexels_images(image_queries)

    # Default images if API fails
    while len(images) < 4:
        images.append(
            {
                "url": "https://images.pexels.com/photos/1105019/pexels-photo-1105019.jpeg",
                "alt": "Microgreens growing",
                "photographer": "Pexels",
            }
        )

    # Article content with real research
    article_html = f"""
<div class="blog-post-content">
    <img src="{images[0]['url']}" alt="{images[0]['alt']}" style="width:100%; max-width:800px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[0]['photographer']}</em></p>

    <p>What if you could grow nutrient-dense superfoods in your kitchen, harvest them in just 7-14 days, and do it all year round with nothing more than a sunny windowsill? Welcome to the world of microgreens—tiny plants that pack an outsized nutritional punch. According to industry research, the <strong>global microgreens market reached $2.82 billion in 2023</strong> and is projected to hit $8.72 billion by 2033, growing at nearly 12% CAGR. This explosive growth reflects both their nutritional value and the joy of growing food at home.</p>

    <h2>What Exactly Are Microgreens?</h2>

    <p>Agricultural experts describe microgreens as "vegetables and herbs harvested seven to 14 days after the seedlings poke up from the soil surface." They've "garnered popularity as a superfood and chefs have embraced them as nutritious garnishes and unexpected pops of flavor and texture."</p>

    <h3>Microgreens vs. Sprouts vs. Baby Greens</h3>
    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Type</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Harvest Time</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Growing Method</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Parts Eaten</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Sprouts</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">2-5 days</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Water only, no soil</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Entire seed, root, and stem</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Microgreens</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">7-14 days</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Soil or growing medium</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Stem and leaves only</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Baby Greens</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">15-40 days</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Full garden conditions</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Young leaves</td>
        </tr>
    </table>

    <h2>The Science: Up to 40x More Nutrients</h2>

    <p>Research from the <strong>USDA Agricultural Research Service</strong> has revealed that microgreens can contain <strong>up to 40 times more nutrients</strong> than their mature counterparts. Scientists have published numerous studies shedding light on "microgreens' nutritional benefits."</p>

    <p>A groundbreaking study by the <strong>American Chemical Society</strong> compared windowsill-grown microgreens to those grown in commercial chambers. The findings were remarkable:</p>

    <blockquote>
        <p>"Despite some nutrients varying between the two environments, both yields were rich in polyphenols and glucosinolates compounds. Polyphenols and glucosinolates have been linked to reducing and blocking inflammation. They've also been documented in helping provide protection from stress, heart disease, heart attacks, colorectal cancer, prostate cancer and breast cancer."</p>
        <cite>— Lindsay Campbell, Modern Farmer</cite>
    </blockquote>

    <img src="{images[1]['url']}" alt="{images[1]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[1]['photographer']}</em></p>

    <h3>Broccoli Microgreens: A Sulforaphane Powerhouse</h3>
    <p>According to Microgreens World, "broccoli microgreens contain up to 10-40 times more nutrients than mature broccoli, including vitamins A, C, E, and K, as well as minerals like calcium, iron, and magnesium." Even more impressive: "Broccoli microgreens can have 10-100 times more sulforaphane"—a potent cancer-fighting compound.</p>

    <h2>Getting Started: What You Need</h2>

    <p>According to agricultural extension specialists, growing microgreens at home is simple and requires minimal equipment:</p>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>Basic Supplies:</strong>
        <ul>
            <li><strong>Containers:</strong> "You can use old food containers and poke some holes at the bottom for water to flow through"</li>
            <li><strong>Growing medium:</strong> Seed starting mix, coconut coir, or potting soil</li>
            <li><strong>Seeds:</strong> Specifically labeled for microgreens or organic vegetable seeds</li>
            <li><strong>Spray bottle:</strong> For gentle watering</li>
            <li><strong>Sunny windowsill:</strong> South-facing preferred (or grow lights)</li>
        </ul>
    </div>

    <h2>Step-by-Step Growing Guide</h2>

    <p>Based on guidance from NC State Cooperative Extension:</p>

    <ol>
        <li><strong>Prepare container:</strong> Fill with 1-2 inches of moistened growing medium</li>
        <li><strong>Sow seeds:</strong> "Add enough seeds to cover the top"—seed spacing is not as critical for microgreens since they grow for such a short time</li>
        <li><strong>Follow seed instructions:</strong> Some seeds need pre-soaking (peas, sunflowers), and some need light to germinate (broccoli, kale) while others don't (peas)</li>
        <li><strong>Mist and cover:</strong> Keep media moist "but not soaked, a spray bottle is great for this!" Cover with a lid or damp paper towel until germination</li>
        <li><strong>Uncover after sprouting:</strong> Once seeds sprout, remove cover and move to windowsill</li>
        <li><strong>Water daily:</strong> "Keep the media moist by spritzing water once or twice a day as needed"</li>
        <li><strong>Harvest:</strong> "After only a week or two, your microgreens should have grown 1-3 inches and have their first true leaves"</li>
    </ol>

    <img src="{images[2]['url']}" alt="{images[2]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[2]['photographer']}</em></p>

    <h2>Best Microgreens for Beginners</h2>

    <p>Industry data shows broccoli leads the market, but here are the easiest varieties to start with:</p>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Variety</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Days to Harvest</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Flavor Profile</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Notes</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Radish</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">5-7</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Spicy, peppery</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Fastest growing, great for beginners</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Sunflower</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">8-12</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Nutty, crunchy</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Pre-soak 8-12 hours; substantial texture</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Pea Shoots</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">8-14</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Sweet, fresh</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Pre-soak; large and satisfying</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Broccoli</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">7-10</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Mild, slightly bitter</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Highest in sulforaphane</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Basil</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">12-18</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Aromatic, herby</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Slower but intensely flavorful</td>
        </tr>
    </table>

    <h2>Windowsill vs. Grow Lights</h2>

    <p>The American Chemical Society study compared windowsill-grown microgreens to those grown in commercial growth chambers. The results were encouraging for home growers:</p>

    <ul>
        <li><strong>Windowsill greens</strong> had higher levels of three flavanol compounds (contributing to dark color and bitter taste)</li>
        <li><strong>Chamber-grown</strong> had higher levels of two glucosinolates (antioxidant compounds)</li>
        <li><strong>Bottom line:</strong> "You can still count on your window-grown sprouts packing a nutritional punch"</li>
    </ul>

    <p>For best results with a windowsill, aim for 4-6 hours of direct sunlight. South-facing windows work best in the Northern Hemisphere.</p>

    <h2>Year-Round Growing Benefits</h2>

    <p>NC State Extension highlights a key advantage: "You can grow plants outside of their normal growing season, like broccoli and leafy greens during the hot summer or sunflowers and basil in the winter." Microgreens also offer a great way to "test if your older garden seeds are still able to germinate!"</p>

    <img src="{images[3]['url']}" alt="{images[3]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[3]['photographer']}</em></p>

    <h2>Harvesting and Storage</h2>

    <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>Harvesting Tips:</strong>
        <ul>
            <li>"Cut them at the bottom using clean scissors" when they're 1-3 inches tall with first true leaves</li>
            <li>Harvest just before use for maximum freshness and nutrition</li>
            <li>If storing, place unwashed microgreens in a container lined with paper towel</li>
            <li>Refrigerate and use within 5-7 days</li>
        </ul>
    </div>

    <h2>How to Use Microgreens</h2>

    <p>According to NC State Extension, "You can eat microgreens on their own as a snack or in dishes like salads, sandwiches, and even on pizza!" Here are more ideas:</p>

    <ul>
        <li><strong>Salads:</strong> Add a nutrient boost to any green salad</li>
        <li><strong>Smoothies:</strong> Blend mild varieties like pea shoots into green smoothies</li>
        <li><strong>Sandwiches & Wraps:</strong> Use as a fresh, crunchy layer</li>
        <li><strong>Garnish:</strong> Top soups, eggs, avocado toast, grain bowls</li>
        <li><strong>Stir-fries:</strong> Add at the very end to preserve nutrients</li>
        <li><strong>Juicing:</strong> Combine with other vegetables for concentrated nutrition</li>
    </ul>

    <h2>Troubleshooting Common Issues</h2>

    <h3>Mold or Fungus</h3>
    <p>Usually caused by overwatering, poor air circulation, or overcrowded seeds. Solution: Improve ventilation, water from bottom if possible, and don't over-seed.</p>

    <h3>Leggy/Stretched Seedlings</h3>
    <p>Not enough light. Move closer to window or supplement with grow lights.</p>

    <h3>Slow Germination</h3>
    <p>Temperature too cold. Most microgreens germinate best at 65-75°F (18-24°C).</p>

    <h3>Seeds Not Sprouting</h3>
    <p>Old seeds may have lost viability. Try fresh seeds or check if pre-soaking is needed.</p>

    <h2>The Growing Market</h2>

    <p>Market research shows that "indoor systems controlled 46% of the microgreens market share in 2024, while vertical farming is on course for the fastest 20.2% CAGR by 2030." This reflects the growing interest in urban food production and year-round growing.</p>

    <p>The US market alone reached $438.35 million in 2024 according to IMARC Group—proof that microgreens have moved from chef's garnish to mainstream superfood.</p>

    <h2>Final Thoughts</h2>

    <p>Growing microgreens on your windowsill is one of the easiest ways to produce fresh, nutrient-dense food at home. With minimal investment, just a week or two of patience, and a sunny spot in your kitchen, you can harvest greens with up to 40 times the nutrition of mature vegetables. It's gardening distilled to its simplest, most rewarding form.</p>

    <p>Start with radish or sunflower seeds—they're forgiving and fast. Once you taste the difference between store-bought and homegrown, you'll likely join the millions discovering why microgreens are the fastest-growing segment of urban agriculture.</p>

</div>
"""

    # Prepare article data
    article_data = {
        "article": {
            "title": "Growing Microgreens on Your Windowsill: The 7-Day Superfood You Can Grow at Home",
            "author": "The Rike",
            "body_html": article_html,
            "tags": "microgreens, indoor gardening, windowsill growing, superfoods, urban farming, sustainable living, nutrition, home gardening",
            "published": True,
            "metafields": [
                {
                    "namespace": "global",
                    "key": "title_tag",
                    "value": "Growing Microgreens on Your Windowsill: 7-Day Superfood at Home",
                    "type": "single_line_text_field",
                },
                {
                    "namespace": "global",
                    "key": "description_tag",
                    "value": "Learn to grow nutrient-dense microgreens on your windowsill in just 7-14 days. With up to 40x more nutrients than mature vegetables, they're the ultimate superfood.",
                    "type": "single_line_text_field",
                },
            ],
        }
    }

    # Publish to Shopify
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }

    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json"

    print("Publishing article: Growing Microgreens on Your Windowsill...")
    print(f"Store: {SHOPIFY_STORE}")
    print(f"Blog ID: {BLOG_ID}")

    response = requests.post(url, headers=headers, json=article_data, timeout=30)

    if response.status_code == 201:
        result = response.json()
        article_id = result["article"]["id"]
        article_handle = result["article"]["handle"]
        print(f"\n✅ SUCCESS! Article published!")
        print(f"Article ID: {article_id}")
        print(f"URL: https://{SHOPIFY_STORE}/blogs/sustainable-living/{article_handle}")
        return result
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        print(response.text)
        return None


if __name__ == "__main__":
    create_article()
