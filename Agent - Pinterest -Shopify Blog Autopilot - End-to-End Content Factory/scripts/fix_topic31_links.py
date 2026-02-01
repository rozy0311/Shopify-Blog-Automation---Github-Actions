#!/usr/bin/env python3
"""
Topic 31: Fermenting Vegetables at Home - REPUBLISH with proper hidden links
Links are clickable but display source name, not URL
"""

import requests
import json
from datetime import datetime

# === CONFIGURATION ===
SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"
PEXELS_API_KEY = "os.environ.get("PEXELS_API_KEY", "")"

# Article to update
ARTICLE_ID = 690503254334  # Topic 31: Fermenting Vegetables


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


def update_article():
    """Update article with proper hidden links"""

    # Get 4 relevant images
    image_queries = [
        "fermented vegetables jars",
        "sauerkraut homemade",
        "kimchi korean food",
        "pickled vegetables healthy",
    ]
    images = get_pexels_images(image_queries)

    # Default images if API fails
    while len(images) < 4:
        images.append(
            {
                "url": "https://images.pexels.com/photos/1435904/pexels-photo-1435904.jpeg",
                "alt": "Fermented vegetables",
                "photographer": "Pexels",
            }
        )

    # Article content with PROPER hidden links (clickable but showing source name, not URL)
    article_html = f"""
<div class="blog-post-content">
    <img src="{images[0]['url']}" alt="{images[0]['alt']}" style="width:100%; max-width:800px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[0]['photographer']}</em></p>

    <p>Fermented vegetables are more than just flavorful additions to your meals—they're powerhouses of health benefits that can support your digestive system, boost your immune response, and even improve your mood. According to <a href="https://www.precedenceresearch.com/fermented-foods-market" target="_blank" rel="noopener">Precedence Research</a>, the <strong>global fermented foods market reached $258.97 billion in 2025</strong> and is projected to reach $394.91 billion by 2034, growing at a CAGR of 4.80%. This explosive growth reflects the rising consumer awareness of gut health and the benefits of fermented foods.</p>

    <h2>Why Fermented Vegetables Matter</h2>

    <p>According to <a href="https://nourishingmeals.com/2025/07/healing-power-fermented-vegetables-gut-health" target="_blank" rel="noopener">Nourishing Meals</a>, "Fermentation is an ancient partnership between humans and microbes. For thousands of years, cultures around the world have used bacteria to preserve and enhance their food—sauerkraut in Germany, kimchi in Korea, cucumber pickles in the Middle East, and umeboshi plums in Japan."</p>

    <p>Fermented vegetables are living foods, rich in:</p>
    <ul>
        <li><strong>Beneficial microorganisms</strong> (primarily lactic acid bacteria) that help suppress harmful microbes</li>
        <li><strong>Bioactive peptides</strong> with anti-inflammatory and immune-supportive effects</li>
        <li><strong>B vitamins and vitamin C</strong>, depending on the vegetable and fermentation process</li>
        <li><strong>Phytonutrients</strong> that remain bioavailable and support detoxification</li>
    </ul>

    <h2>The Science Behind Lacto-Fermentation</h2>

    <p>Lacto-fermentation is a microbial preservation process that uses lactic acid bacteria (LAB)—primarily Lactobacillus, Leuconostoc, and Pediococcus species—naturally found on fresh vegetables. According to food scientists:</p>

    <blockquote>
        <p>"In an anaerobic (oxygen-free), salty brine, these microbes consume sugars and starches from the plant tissue, convert them into lactic acid, which lowers the pH, produce organic acids, bioactive peptides, and carbon dioxide, and inhibit the growth of harmful bacteria."</p>
        <cite>— Nourishing Meals</cite>
    </blockquote>

    <img src="{images[1]['url']}" alt="{images[1]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[1]['photographer']}</em></p>

    <h2>Health Benefits of Fermented Vegetables</h2>

    <p>According to <a href="https://www.ucihealth.org/blog/2024/09/gut-health-and-fermented-foods" target="_blank" rel="noopener">UCI Health</a>:</p>

    <blockquote>
        <p>"Greek yogurt, kimchi, sauerkraut, apple cider vinegar, miso, kombucha, kefir and sourdough bread are just a few examples of beneficial fermented foods. All can be found in most grocery stores, making them a simple addition to your everyday meal plans."</p>
        <cite>— Katie Rankell, Director of the UCI Health Weight Management Program</cite>
    </blockquote>

    <p>Research from <a href="https://gatorcare.org/2025/05/05/food-for-thought-fermented-foods/" target="_blank" rel="noopener">GatorCare</a> highlights three key benefits:</p>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Benefit</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">How It Works</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Gut Health</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Rich in probiotics that support a healthy digestive system and enhance nutrient absorption</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Immune Support</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Regular consumption can bolster your immune system, helping your body fend off illnesses</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Reduced Inflammation</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">UC Davis study found sauerkraut helped protect intestinal cells from inflammatory damage</td>
        </tr>
    </table>

    <h2>Vegetables Perfect for Fermentation</h2>

    <p>According to fermentation experts, these vegetables work best:</p>

    <ul>
        <li><strong>Cabbage</strong> (for sauerkraut, kimchi, curtido)</li>
        <li><strong>Carrots</strong> (with garlic, ginger, or dill)</li>
        <li><strong>Beets</strong> (alone or with herbs and onions)</li>
        <li><strong>Radishes</strong> (especially daikon and watermelon radish)</li>
        <li><strong>Cauliflower and broccoli florets</strong></li>
        <li><strong>Green beans</strong></li>
        <li><strong>Pickling cucumbers</strong> (for traditional dill pickles)</li>
        <li><strong>Peppers</strong> (sweet or hot for hot sauce)</li>
    </ul>

    <img src="{images[2]['url']}" alt="{images[2]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[2]['photographer']}</em></p>

    <h2>Basic Sauerkraut Recipe</h2>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>Ingredients:</strong>
        <ul>
            <li>1 medium head green cabbage (about 2 lbs)</li>
            <li>1 tablespoon sea salt (non-iodized)</li>
        </ul>

        <strong>Instructions:</strong>
        <ol>
            <li>Remove outer leaves from cabbage; set aside 1-2 clean leaves</li>
            <li>Quarter, core, and thinly slice the cabbage</li>
            <li>Place in large bowl and sprinkle with salt</li>
            <li>Massage cabbage for 5-10 minutes until it releases liquid</li>
            <li>Pack tightly into a clean quart jar, pressing down firmly</li>
            <li>Place reserved leaf on top; weigh down to keep cabbage submerged</li>
            <li>Cover with cloth; let ferment at room temperature 3-10 days</li>
            <li>Taste daily; refrigerate when desired sourness is reached</li>
        </ol>
    </div>

    <h2>How Much to Eat Daily</h2>

    <p>According to nutrition experts, "Just 1 to 3 tablespoons per day can make a meaningful difference. The microbes, enzymes, and acids help support digestion, improve mineral absorption, and regulate inflammation, especially when paired with a diverse, plant-rich diet."</p>

    <h2>Easy Ways to Incorporate Fermented Vegetables</h2>

    <ul>
        <li><strong>Breakfast:</strong> Top eggs or avocado toast with a spoonful of kimchi or sauerkraut</li>
        <li><strong>Lunch:</strong> Add to salads, sandwiches, or grain bowls</li>
        <li><strong>Dinner:</strong> Serve as a side with curry, grilled fish, or slow-cooked meats</li>
        <li><strong>Snacks:</strong> Enjoy fermented carrot sticks for a crunchy, probiotic-rich treat</li>
    </ul>

    <img src="{images[3]['url']}" alt="{images[3]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[3]['photographer']}</em></p>

    <h2>Troubleshooting Common Issues</h2>

    <h3>Mold on Top</h3>
    <p>Keep vegetables fully submerged in brine. "Mold cannot grow without oxygen, so the brine line is your protective barrier."</p>

    <h3>Soft or Mushy Texture</h3>
    <p>Use fresh, crisp vegetables and proper salt ratio (2% by weight). Ferment in a cooler location.</p>

    <h3>Too Salty</h3>
    <p>Rinse before eating or reduce salt in next batch. Standard ratio is 1-2 tablespoons salt per pound of vegetables.</p>

    <h2>The Growing Market for Fermented Foods</h2>

    <p>According to <a href="https://www.mordorintelligence.com/industry-reports/fermented-foods-beverages-market" target="_blank" rel="noopener">Mordor Intelligence</a>, "The fermented foods and beverages market is projected to grow from $318.20 billion in 2025 to $434.60 billion by 2030." The Asia-Pacific region leads with 33.53% market share, driven by deep-rooted cultural consumption of fermented foods like kimchi, miso, and tempeh.</p>

    <h2>Final Thoughts</h2>

    <p>Fermented vegetables remind us that healing can be a simple act of daily nourishment. Sometimes it begins with just a few humble ingredients, a glass jar, and a pinch of salt—transforming not just our food, but our inner landscape. Start with simple sauerkraut, then experiment with kimchi, fermented carrots, or pickled jalapeños. Your gut—and your taste buds—will thank you.</p>
</div>
"""

    # Update article
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }

    url = f"https://{SHOPIFY_STORE}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{ARTICLE_ID}.json"

    data = {"article": {"id": ARTICLE_ID, "body_html": article_html}}

    print(f"Updating article: Fermenting Vegetables at Home (ID: {ARTICLE_ID})...")

    response = requests.put(url, headers=headers, json=data, timeout=30)

    if response.status_code == 200:
        print(f"\n✅ SUCCESS! Article updated with proper hidden links!")
        print(
            f"URL: https://{SHOPIFY_STORE}/blogs/sustainable-living/fermenting-vegetables-at-home-a-beginners-guide-to-sauerkraut-kimchi-more-1"
        )
        return True
    else:
        print(f"\n❌ ERROR: {response.status_code}")
        print(response.text)
        return False


if __name__ == "__main__":
    update_article()
