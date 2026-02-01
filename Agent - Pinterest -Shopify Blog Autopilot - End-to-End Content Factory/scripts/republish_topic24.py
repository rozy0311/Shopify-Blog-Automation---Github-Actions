#!/usr/bin/env python3
"""
Topic 24: Natural Fabric Dyes from Food Scraps - REPUBLISH
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
    print("Finding article: Natural Fabric Dyes...")
    article_id = find_article_by_title("fabric dyes")

    if not article_id:
        print("❌ Article not found!")
        return

    print(f"Found article ID: {article_id}")

    # Get images
    image_queries = [
        "natural fabric dye textile colorful",
        "avocado pit pink dye craft",
        "onion skins yellow orange",
        "tie dye fabric handmade",
    ]
    images = get_pexels_images(image_queries)

    while len(images) < 4:
        images.append(
            {
                "url": "https://images.pexels.com/photos/4622893/pexels-photo-4622893.jpeg",
                "alt": "Natural dyed fabric",
                "photographer": "Pexels",
            }
        )

    # Article content with PROPER hidden links
    article_html = f"""
<div class="blog-post-content">
    <img src="{images[0]['url']}" alt="{images[0]['alt']}" style="width:100%; max-width:800px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[0]['photographer']}</em></p>

    <p>Those avocado pits, onion skins, and coffee grounds you throw away? They can create stunning, eco-friendly fabric dyes. According to <a href="https://goodonyou.eco/textile-dyes-pollution/" target="_blank" rel="noopener">Good On You</a>, "The UN Environment Program reported that textile dyeing is the <strong>second largest polluter of water in the world</strong>."</p>

    <p>As <a href="https://www.sciencedirect.com/science/article/abs/pii/S2214714425021440" target="_blank" rel="noopener">ScienceDirect</a> reports, "The global textile industry is responsible for nearly 20% of industrial water pollution, releasing an estimated 40,000–50,000 tons of dyes annually."</p>

    <p>Natural dyes from food scraps offer a beautiful, sustainable alternative—and they're easier to make than you think.</p>

    <h2>Why Choose Natural Dyes?</h2>

    <p>According to <a href="https://healtheplanet.com/100-ways-to-heal-the-planet/textile-dyeing" target="_blank" rel="noopener">Heal the Planet</a>:</p>
    <ul>
        <li>72 toxic chemicals have been identified in fresh water systems coming solely from textile dyeing</li>
        <li>20% of all industrial water pollution is caused by fabric dyes and treatments</li>
        <li>It's estimated that 10,000 different synthetic dyes are used industrially</li>
        <li>Synthetic dyes contain endocrine disruptors</li>
    </ul>

    <p>As <a href="https://threadcollective.com.au/blogs/dyeing/natural-dyeing-kitchen-scraps" target="_blank" rel="noopener">Thread Collective</a> explains, "Dyeing with kitchen scraps is not just eco-friendly; it's a creative way to connect with nature and your materials. By repurposing waste, you avoid synthetic chemicals and reduce your environmental footprint while saving money."</p>

    <h2>Kitchen Scraps Color Guide</h2>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Color</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Food Scraps to Use</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong style="color: #d4a373;">Pink/Blush</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Avocado skins and pits</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong style="color: #e9c46a;">Yellow/Gold</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Yellow onion skins, lemon peels, turmeric</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong style="color: #e76f51;">Orange</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Red onion skins, paprika, pomegranate peels</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong style="color: #8b4513;">Brown</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Coffee grounds, black tea, walnut hulls</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong style="color: #9b59b6;">Purple/Blue</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Red cabbage leaves, blueberries, blackberries</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong style="color: #2ecc71;">Green</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Spinach, artichokes, fresh herbs</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong style="color: #c0392b;">Red</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Beet peels, cherries, raspberries</td>
        </tr>
    </table>

    <img src="{images[1]['url']}" alt="{images[1]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[1]['photographer']}</em></p>

    <h2>Before You Start: Essential Tips</h2>

    <h3>1. Use Natural Fabrics Only</h3>
    <p>According to <a href="https://www.thistle.co/learn/thistle-thoughts/make-natural-dye-from-food-waste" target="_blank" rel="noopener">Thistle</a>, "Choose only 100% natural fibers like cotton, linen, wool, and silk. Natural dye won't 'stick' to synthetic fabrics."</p>

    <h3>2. Understand Mordants</h3>
    <p>A mordant is a fixative that helps dye bind to fabric and prevents fading. Common mordants include:</p>
    <ul>
        <li><strong>Alum (aluminum potassium sulfate):</strong> Safest and most common</li>
        <li><strong>Cream of tartar:</strong> Brightens colors</li>
        <li><strong>Iron:</strong> Darkens/saddens colors</li>
        <li><strong>Tannins:</strong> Natural mordant found in some dyes</li>
    </ul>

    <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>💡 No-Mordant Option:</strong><br>
        According to Thistle, "Since avocado has naturally-occurring tannins, you don't need to use a mordant when making natural dye with avocado skin and peels." Black tea is another tannin-rich dye that doesn't require mordanting.
    </div>

    <h2>How to Make Natural Dye: Basic Process</h2>

    <ol>
        <li><strong>Collect and prep scraps:</strong> Gather enough scraps (about 1:1 ratio to fabric weight)</li>
        <li><strong>Pre-wash fabric:</strong> Remove any finishes or residues</li>
        <li><strong>Mordant fabric:</strong> Soak in alum solution for 1 hour (unless using avocado or tea)</li>
        <li><strong>Make dye bath:</strong> Simmer scraps in water for 1-4 hours</li>
        <li><strong>Strain:</strong> Remove solids, keep liquid</li>
        <li><strong>Dye fabric:</strong> Submerge fabric and simmer 1 hour or soak overnight</li>
        <li><strong>Rinse and dry:</strong> Rinse in cool water until clear, hang to dry</li>
    </ol>

    <img src="{images[2]['url']}" alt="{images[2]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[2]['photographer']}</em></p>

    <h2>Detailed Recipe: Avocado Pink Dye</h2>

    <p>According to <a href="https://lacreativemama.com/how-to-make-natural-dye/" target="_blank" rel="noopener">La Creative Mama</a>, "Avocados are a great natural source of color. Avocado skins will provide you with a blush color. Avocado pits will deliver a beautiful pink color. Mixing avocado skins and pits will result in a deep rich pink tone."</p>

    <h3>Instructions from Thistle:</h3>
    <ol>
        <li>Save all avocado peels and pits until you have around 6 full avocado skins</li>
        <li>Peel the skins into pieces and place these and the pits in 4-5 cups of water</li>
        <li>Put water in a pot on the stove and make sure water is simmering, not boiling</li>
        <li>Keep the water on simmer for around 3-4 hours (checking in occasionally)</li>
        <li>Remove dyed water from pot and place in clear glass bowl</li>
        <li>Place white item in dye and let it soak overnight</li>
        <li>Remove item from dye and let it dry out</li>
        <li>Rinse item under water to remove any excess dye or avocado remnants</li>
    </ol>

    <h2>Recipe: Onion Skin Golden Yellow</h2>

    <p>According to Thread Collective, "Yellow onion skins produce vibrant yellows and golden-orange hues, while red onion skins create rich earthy browns, orange tones and even greens depending on choice of mordant."</p>

    <h3>Collection Tip:</h3>
    <p>"When peeling onions, save the outer papery layers and store them in a dry jar or paper bag. Onion skins are an excellent choice for beginners."</p>

    <h3>Instructions:</h3>
    <ol>
        <li>Collect skins from about 12 onions (approximately 2 cups loosely packed)</li>
        <li>Mordant fabric in alum solution first (2 tablespoons alum per gallon water)</li>
        <li>Cover onion skins with water and simmer 1 hour</li>
        <li>Strain out skins</li>
        <li>Add wet, mordanted fabric</li>
        <li>Simmer 1 hour, stirring occasionally</li>
        <li>Let cool in dye bath for deeper color</li>
        <li>Rinse until water runs clear</li>
    </ol>

    <h2>Recipe: Coffee Brown</h2>

    <p>According to Thread Collective, "Coffee grounds create warm brown tones. Collect used coffee grounds, dry them thoroughly, and store in an airtight container to prevent mould."</p>

    <h3>Instructions:</h3>
    <ol>
        <li>Collect about 6 cups of used coffee grounds</li>
        <li>Simmer grounds in 1 gallon water for 1 hour</li>
        <li>Strain out grounds</li>
        <li>Add pre-washed fabric (no mordant needed—coffee contains natural tannins)</li>
        <li>Simmer 1-2 hours for deeper color</li>
        <li>Allow to cool in dye bath overnight</li>
        <li>Rinse and dry</li>
    </ol>

    <img src="{images[3]['url']}" alt="{images[3]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[3]['photographer']}</em></p>

    <h2>Storing Your Kitchen Scraps</h2>

    <p>According to Thread Collective's storage tips:</p>
    <ul>
        <li><strong>Avocado pits and skins:</strong> Clean thoroughly, freeze until ready to use</li>
        <li><strong>Onion skins:</strong> Store in dry jar or paper bag at room temperature</li>
        <li><strong>Coffee grounds:</strong> Dry thoroughly, store in airtight container</li>
        <li><strong>Tea bags:</strong> Dry completely, store in jar</li>
        <li><strong>Red cabbage:</strong> Refrigerate for short-term, freeze for later</li>
    </ul>

    <h2>Project Ideas</h2>

    <p>According to Thread Collective, here are creative ways to use your naturally-dyed fabrics:</p>
    <ul>
        <li><strong>Tie-dye scarves:</strong> Use vibrant scraps like onion skins or red cabbage</li>
        <li><strong>Tote bags:</strong> Experiment with earthy tones from coffee or tea</li>
        <li><strong>Pillowcases:</strong> Achieve soft pastels using avocado</li>
        <li><strong>Cloth napkins:</strong> Create a set in coordinating natural tones</li>
        <li><strong>Wall hangings:</strong> Layer different dyed fabrics for artistic effect</li>
    </ul>

    <h2>Tips for Better Results</h2>

    <ul>
        <li><strong>Longer = darker:</strong> The longer you simmer scraps and soak fabric, the deeper the color</li>
        <li><strong>Pre-wet fabric:</strong> Always add damp fabric to dye bath for even color</li>
        <li><strong>Use enough water:</strong> Fabric should move freely in the dye bath</li>
        <li><strong>Avoid first wash:</strong> Wait a few days before washing naturally-dyed items</li>
        <li><strong>Wash gently:</strong> Use cold water and mild soap to preserve color</li>
        <li><strong>Dry in shade:</strong> Direct sunlight can fade natural dyes</li>
    </ul>

    <h2>Final Thoughts</h2>

    <p>With the textile industry responsible for 20% of global water pollution, choosing natural dyes is a meaningful way to reduce your environmental impact. Plus, those avocado pits and onion skins were headed for the trash anyway—now they can create beautiful, one-of-a-kind textiles. Start collecting your scraps, experiment with colors, and enjoy the creative process of turning food waste into wearable art.</p>
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
