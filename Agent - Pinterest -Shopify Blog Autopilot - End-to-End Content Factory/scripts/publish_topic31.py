#!/usr/bin/env python3
"""
Topic 31: Fermenting Vegetables at Home
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
        "kimchi fermented vegetables jar",
        "sauerkraut cabbage fermenting",
        "pickled vegetables mason jar",
        "fermented food preparation kitchen",
    ]
    images = get_pexels_images(image_queries)

    # Default images if API fails
    while len(images) < 4:
        images.append(
            {
                "url": "https://images.pexels.com/photos/5945559/pexels-photo-5945559.jpeg",
                "alt": "Fermented vegetables in jar",
                "photographer": "Pexels",
            }
        )

    # Article content with real research
    article_html = f"""
<div class="blog-post-content">
    <img src="{images[0]['url']}" alt="{images[0]['alt']}" style="width:100%; max-width:800px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[0]['photographer']}</em></p>

    <p>For thousands of years, cultures around the world have harnessed the power of fermentation to preserve food and enhance nutrition. Today, as we better understand the importance of gut health, fermented vegetables are experiencing a remarkable renaissance. According to <a href="https://www.precedenceresearch.com/fermented-foods-market" target="_blank" rel="noopener">Precedence Research</a>, the <strong>global fermented foods market is valued at $258.97 billion in 2025</strong> and is projected to reach $394.91 billion by 2034—a testament to growing consumer awareness of these ancient foods' benefits.</p>

    <h2>The Science Behind Lacto-Fermentation</h2>

    <p>Lacto-fermentation is the process that transforms ordinary vegetables into probiotic powerhouses. According to <a href="https://nourishingmeals.com/2025/07/healing-power-fermented-vegetables-gut-health" target="_blank" rel="noopener">Nourishing Meals</a>, this process uses lactic acid bacteria (LAB)—primarily Lactobacillus, Leuconostoc, and Pediococcus species—naturally found on fresh vegetables.</p>

    <p>Here's what happens during fermentation:</p>
    <ul>
        <li><strong>Bacteria consume sugars</strong> and starches from the plant tissue</li>
        <li><strong>Convert them into lactic acid</strong>, which lowers the pH</li>
        <li><strong>Produce organic acids, bioactive peptides, and carbon dioxide</strong></li>
        <li><strong>Inhibit harmful bacteria</strong> while preserving the vegetables</li>
    </ul>

    <p>This process also enhances nutrition. Certain strains of lactic acid bacteria are capable of synthesizing B vitamins, particularly <strong>riboflavin (B2) and folate (B9)</strong>, potentially increasing these nutrients in the final product.</p>

    <blockquote>
        <p>"Fermented vegetables are more than a flavorful addition to your plate—they're living foods, rich in beneficial microorganisms that help suppress harmful microbes and support the growth of your native gut flora."</p>
        <cite>— Ali Segersten, Nourishing Meals</cite>
    </blockquote>

    <h2>Health Benefits: What the Research Says</h2>

    <img src="{images[1]['url']}" alt="{images[1]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[1]['photographer']}</em></p>

    <p>According to <a href="https://www.ucihealth.org/blog/2024/09/gut-health-and-fermented-foods" target="_blank" rel="noopener">UCI Health</a>, "the live microorganisms in fermented foods reduce the absorption of cholesterol in the gut, lowering your risk for atherosclerosis—a buildup of cholesterol in the arteries that can cause blockages."</p>

    <p>Scientific research supports multiple benefits:</p>

    <h3>Key Probiotic Strains in Fermented Vegetables</h3>
    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Strain</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Found In</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Benefits</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Lactobacillus sakei</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Kimchi</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Inhibits pathogens, supports nasal and skin microbiota, may reduce histamine responses</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Leuconostoc mesenteroides</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Sauerkraut, Kimchi</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Initiates lactic acid production, kick-starts preservation</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Pediococcus pentosaceus</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Various ferments</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Produces bacteriocins, reduces intestinal inflammation</td>
        </tr>
    </table>

    <p>Published research in <em>Nutrients</em> journal (Leeuwendaal et al., 2022) confirms that "fermented foods, health and the gut microbiome" are closely connected, while a study in the <em>Journal of Medicinal Food</em> (Park et al., 2014) documents the specific "health benefits of kimchi as a probiotic food."</p>

    <h2>Vegetables Perfect for Fermentation</h2>

    <p>According to fermentation experts, these vegetables work best for lacto-fermentation:</p>

    <ul>
        <li><strong>Cabbage</strong> — for sauerkraut, kimchi, curtido</li>
        <li><strong>Carrots</strong> — with garlic, ginger, or dill</li>
        <li><strong>Beets</strong> — alone or with herbs and onions</li>
        <li><strong>Radishes</strong> — especially daikon and watermelon radish</li>
        <li><strong>Cauliflower and broccoli florets</strong></li>
        <li><strong>Cucumbers</strong> — for traditional dill pickles</li>
        <li><strong>Peppers</strong> — sweet or hot, for fermented hot sauce</li>
        <li><strong>Green beans, turnips, kohlrabi</strong></li>
    </ul>

    <h2>Basic Sauerkraut Recipe</h2>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>Equipment Needed:</strong>
        <ul>
            <li>Wide-mouth quart mason jar</li>
            <li>Fermentation weight or small jar that fits inside</li>
            <li>Clean cloth or coffee filter and rubber band</li>
        </ul>

        <strong>Ingredients:</strong>
        <ul>
            <li>1 medium cabbage (about 2 lbs)</li>
            <li>1 tablespoon sea salt (non-iodized)</li>
        </ul>

        <strong>Instructions:</strong>
        <ol>
            <li><strong>Prepare cabbage:</strong> Remove outer leaves, quarter, core, and slice thinly</li>
            <li><strong>Salt and massage:</strong> Place in bowl, add salt, massage firmly for 5-10 minutes until brine forms</li>
            <li><strong>Pack jar:</strong> Transfer to clean jar, pressing down firmly after each handful</li>
            <li><strong>Submerge:</strong> Ensure cabbage is completely covered by brine (add a bit of salted water if needed)</li>
            <li><strong>Weight down:</strong> Place weight on top to keep cabbage submerged</li>
            <li><strong>Cover and wait:</strong> Cover with cloth, secure with rubber band, leave at room temperature (65-75°F)</li>
            <li><strong>Ferment:</strong> Taste after 3 days. Most sauerkraut is ready in 1-4 weeks</li>
        </ol>
    </div>

    <img src="{images[2]['url']}" alt="{images[2]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[2]['photographer']}</em></p>

    <h2>Simple Kimchi Recipe</h2>

    <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ffc107;">
        <strong>Ingredients:</strong>
        <ul>
            <li>2 lbs napa cabbage</li>
            <li>1/4 cup sea salt</li>
            <li>2 tablespoons gochugaru (Korean red pepper flakes)</li>
            <li>1 tablespoon fish sauce or soy sauce (for vegan version)</li>
            <li>1 teaspoon sugar</li>
            <li>4 cloves garlic, minced</li>
            <li>1 tablespoon fresh ginger, grated</li>
            <li>4 scallions, chopped</li>
        </ul>

        <strong>Instructions:</strong>
        <ol>
            <li><strong>Salt cabbage:</strong> Cut cabbage into 2-inch pieces, toss with salt, let sit 2 hours</li>
            <li><strong>Rinse and drain:</strong> Rinse 3 times, squeeze out excess water</li>
            <li><strong>Make paste:</strong> Mix gochugaru, fish sauce, sugar, garlic, and ginger</li>
            <li><strong>Combine:</strong> Massage paste into cabbage, add scallions</li>
            <li><strong>Pack and ferment:</strong> Pack tightly into jar, leave 1-inch headspace. Ferment 3-5 days at room temperature, then refrigerate</li>
        </ol>
    </div>

    <h2>The 2% Salt Rule</h2>

    <p>For most vegetable ferments, the golden ratio is <strong>2% salt by weight</strong>. Here's how to calculate it:</p>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Vegetable Weight</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Salt Needed (2%)</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;">500g (about 1 lb)</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">10g (about 2 teaspoons)</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;">1000g (about 2 lbs)</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">20g (about 1 tablespoon)</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;">2000g (about 4 lbs)</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">40g (about 2 tablespoons)</td>
        </tr>
    </table>

    <blockquote>
        <p>"Greek yogurt, kimchi, sauerkraut, apple cider vinegar, miso, kombucha, kefir and sourdough bread are just a few examples of beneficial fermented foods. All can be found in most grocery stores, making them a simple addition to your everyday meal plans."</p>
        <cite>— Katie Rankell, Director, UCI Health Weight Management Program</cite>
    </blockquote>

    <h2>Troubleshooting Common Issues</h2>

    <h3>White Film on Top (Kahm Yeast)</h3>
    <p>This harmless yeast can form on the surface when vegetables aren't fully submerged. Simply skim it off—the ferment underneath is still safe to eat.</p>

    <h3>Soft or Mushy Vegetables</h3>
    <p>Usually caused by too much salt, too high temperature, or over-fermentation. Try fermenting in a cooler spot (60-70°F) for crunchier results.</p>

    <h3>Not Sour Enough</h3>
    <p>Give it more time! Fermentation slows in cooler temperatures. Warmer environments (70-75°F) speed up the process.</p>

    <h3>Pink Sauerkraut</h3>
    <p>This can happen when too much salt is used or the ferment is exposed to light. While safe to eat, it may taste overly salty.</p>

    <h2>How to Enjoy Fermented Vegetables Daily</h2>

    <img src="{images[3]['url']}" alt="{images[3]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[3]['photographer']}</em></p>

    <p>According to nutrition experts, <strong>just 1-3 tablespoons per day can make a meaningful difference</strong>. The microbes, enzymes, and acids help support digestion, improve mineral absorption, and regulate inflammation.</p>

    <h3>Easy Ways to Incorporate Fermented Veggies:</h3>
    <ul>
        <li>Top a warm egg and veggie scramble with a spoonful of kraut</li>
        <li>Add to soups or stews just before serving (to preserve probiotic benefits)</li>
        <li>Tuck into tacos and lettuce wraps for a zingy contrast</li>
        <li>Stir into salads or grain bowls</li>
        <li>Serve alongside cheese boards for added crunch and color</li>
        <li>Layer onto avocado toast or hummus crackers</li>
    </ul>

    <h2>Market Trends: Why Fermented Foods Are Booming</h2>

    <p>The numbers tell a compelling story. According to <a href="https://www.gminsights.com/industry-analysis/fermented-food-market" target="_blank" rel="noopener">Global Market Insights</a>, the fermented food market is growing at a <strong>7% CAGR</strong> and will reach $248.2 billion by 2034. Key drivers include:</p>

    <ul>
        <li>Increasing awareness of digestive health</li>
        <li>Consumer demand for probiotic-rich, naturally preserved foods</li>
        <li>Clean-label attitudes and artisanal flavor preferences</li>
        <li>Growing scientific evidence supporting gut microbiome health</li>
    </ul>

    <h2>Storage Tips</h2>

    <ul>
        <li><strong>Refrigeration:</strong> Once fermentation reaches your desired flavor, move to refrigerator to slow the process</li>
        <li><strong>Shelf life:</strong> Properly fermented vegetables can last 6+ months refrigerated</li>
        <li><strong>Always keep submerged:</strong> Vegetables above the brine can mold—push them back down</li>
        <li><strong>Use clean utensils:</strong> Never double-dip or use dirty utensils in your ferment</li>
    </ul>

    <h2>Final Thoughts</h2>

    <p>Fermenting vegetables at home connects you to an ancient tradition while providing modern health benefits. With just salt, vegetables, and a bit of patience, you can create probiotic-rich foods that support your gut microbiome, preserve seasonal produce, and add incredible flavor to your meals.</p>

    <p>Start with a simple sauerkraut, taste the difference, and you'll understand why fermented foods have endured for thousands of years across every culture on Earth.</p>

    <hr style="margin: 30px 0;">

    <h3>References</h3>
    <ol style="font-size: 0.9em; color: #666;">
        <li>Precedence Research. "Fermented Foods Market Size, Share and Trends 2025 to 2034." <a href="https://www.precedenceresearch.com/fermented-foods-market" target="_blank">precedenceresearch.com</a></li>
        <li>Global Market Insights. "Fermented Food Market Size 2025-2034." <a href="https://www.gminsights.com/industry-analysis/fermented-food-market" target="_blank">gminsights.com</a></li>
        <li>UCI Health. "Gut Health and Fermented Foods." September 2024. <a href="https://www.ucihealth.org/blog/2024/09/gut-health-and-fermented-foods" target="_blank">ucihealth.org</a></li>
        <li>Segersten, Ali. "The Healing Power of Fermented Vegetables for Gut Health." Nourishing Meals, July 2025. <a href="https://nourishingmeals.com/2025/07/healing-power-fermented-vegetables-gut-health" target="_blank">nourishingmeals.com</a></li>
        <li>Leeuwendaal, N. K., et al. "Fermented foods, health and the gut microbiome." Nutrients, 14(7), 1527. 2022.</li>
        <li>Park, K. Y., et al. "Health benefits of kimchi as a probiotic food." Journal of Medicinal Food, 17(1), 6–20. 2014.</li>
    </ol>
</div>
"""

    # Prepare article data
    article_data = {
        "article": {
            "title": "Fermenting Vegetables at Home: A Beginner's Guide to Sauerkraut, Kimchi & More",
            "author": "The Rike",
            "body_html": article_html,
            "tags": "fermented vegetables, sauerkraut, kimchi, lacto fermentation, probiotics, gut health, sustainable living, food preservation",
            "published": True,
            "metafields": [
                {
                    "namespace": "global",
                    "key": "title_tag",
                    "value": "Fermenting Vegetables at Home: Guide to Sauerkraut, Kimchi & Probiotics",
                    "type": "single_line_text_field",
                },
                {
                    "namespace": "global",
                    "key": "description_tag",
                    "value": "Learn to ferment vegetables at home with easy sauerkraut and kimchi recipes. Discover the gut health benefits of lacto-fermentation and start making probiotic-rich foods today.",
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

    print("Publishing article: Fermenting Vegetables at Home...")
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
