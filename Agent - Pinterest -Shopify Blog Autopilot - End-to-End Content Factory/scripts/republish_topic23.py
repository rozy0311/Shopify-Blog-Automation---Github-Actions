#!/usr/bin/env python3
"""
Topic 23: Growing Herbs Indoors Year-Round - REPUBLISH
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
    print("Finding article: Growing Herbs Indoors...")
    article_id = find_article_by_title("herbs indoors")

    if not article_id:
        print("❌ Article not found!")
        return

    print(f"Found article ID: {article_id}")

    # Get images
    image_queries = [
        "indoor herb garden kitchen window",
        "basil plant potted herbs",
        "rosemary thyme fresh herbs",
        "grow light indoor plants",
    ]
    images = get_pexels_images(image_queries)

    while len(images) < 4:
        images.append(
            {
                "url": "https://images.pexels.com/photos/4503273/pexels-photo-4503273.jpeg",
                "alt": "Indoor herbs",
                "photographer": "Pexels",
            }
        )

    # Article content with PROPER hidden links
    article_html = f"""
<div class="blog-post-content">
    <img src="{images[0]['url']}" alt="{images[0]['alt']}" style="width:100%; max-width:800px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[0]['photographer']}</em></p>

    <p>Fresh herbs make every dish better, but supermarket bunches often wilt before you can use them. The solution? Grow your own indoors—year-round. According to <a href="https://www.mordorintelligence.com/industry-reports/fresh-herbs-market" target="_blank" rel="noopener">Mordor Intelligence</a>, <strong>the global fresh herbs market reached $4.23 billion in 2025</strong> and is forecast to reach $6.30 billion by 2030. Basil alone accounts for 32% of the market share.</p>

    <h2>Why Grow Herbs Indoors?</h2>

    <ul>
        <li><strong>Year-round harvest:</strong> No more seasonal limitations</li>
        <li><strong>Save money:</strong> A single basil plant pays for itself in weeks</li>
        <li><strong>Maximum freshness:</strong> Snip what you need moments before cooking</li>
        <li><strong>Convenience:</strong> No trips to the store for forgotten ingredients</li>
        <li><strong>Less waste:</strong> No more wilted herbs thrown away</li>
    </ul>

    <h2>Best Herbs for Indoor Growing</h2>

    <p>As noted on <a href="https://www.facebook.com/groups/zone6bgarden/posts/25249858574616587/" target="_blank" rel="noopener">gardening forums</a>, "Some easy herbs to grow indoors are rosemary, parsley, chives, mint, basil, thyme, oregano, cilantro and sage. Getting set up is easy."</p>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Herb</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Light Needs</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Difficulty</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Best For</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Basil</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">6+ hours direct</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Easy</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Italian dishes, pesto, salads</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Mint</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">4-6 hours</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Very Easy</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Tea, cocktails, desserts</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Chives</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">4-6 hours</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Very Easy</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Eggs, potatoes, soups</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Rosemary</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">6+ hours direct</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Moderate</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Roasts, breads, potatoes</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Thyme</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">6+ hours direct</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Moderate</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Soups, stews, roasted veggies</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Parsley</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">4-6 hours</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Easy</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Almost everything</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Oregano</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">6+ hours</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Easy</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Pizza, Mediterranean dishes</td>
        </tr>
    </table>

    <img src="{images[1]['url']}" alt="{images[1]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[1]['photographer']}</em></p>

    <h2>Essential Requirements for Indoor Herbs</h2>

    <h3>1. Light</h3>

    <p>According to <a href="https://www.bluezones.com/2024/12/boosting-your-immune-system-with-indoor-grown-herbs-this-winter/" target="_blank" rel="noopener">Blue Zones</a>, "Find a bright spot in your home where the herbs can receive at least six hours of sunlight a day. South-facing windows are ideal."</p>

    <p>As <a href="https://growcycle.com/learn/best-herbs-to-grow-indoors-year-round-freshness" target="_blank" rel="noopener">Growcycle</a> notes, "Most herbs, such as basil, rosemary, and thyme, require about 6 hours of direct sunlight."</p>

    <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>💡 No Sunny Windows?</strong><br>
        Consider a grow light! LED grow lights are affordable, energy-efficient, and can provide full-spectrum light for herbs. Position lights 6-12 inches above plants and run for 12-14 hours daily.
    </div>

    <h3>2. Containers</h3>

    <ul>
        <li>Choose pots with drainage holes (critical!)</li>
        <li>Terracotta pots work well—they wick away excess moisture</li>
        <li>Size matters: Most herbs need at least a 6-inch pot</li>
        <li>Consider self-watering containers for consistency</li>
    </ul>

    <h3>3. Soil</h3>

    <p>Use a high-quality potting mix (not garden soil). Look for:</p>
    <ul>
        <li>Good drainage properties</li>
        <li>Perlite or vermiculite for aeration</li>
        <li>Organic matter for nutrients</li>
    </ul>

    <img src="{images[2]['url']}" alt="{images[2]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[2]['photographer']}</em></p>

    <h2>Herb-Specific Growing Tips</h2>

    <p>According to <a href="https://mgnv.org/herbs/a-complete-guide-to-growing-herbs-indoors/" target="_blank" rel="noopener">Master Gardeners of Northern Virginia</a>, "Some herbs have specific needs—for instance, basil can handle being consistently moist, but not wet. Rosemary and thyme prefer drier soil."</p>

    <h3>Basil</h3>
    <ul>
        <li>Loves warmth (60-70°F minimum)</li>
        <li>Keep soil consistently moist</li>
        <li>Pinch off flower buds to encourage bushy growth</li>
        <li>Harvest from the top to promote branching</li>
    </ul>

    <h3>Mint</h3>
    <ul>
        <li>Grows aggressively—plant alone!</li>
        <li>Tolerates less light than other herbs</li>
        <li>Keep soil moist but not waterlogged</li>
        <li>Cut back regularly to prevent legginess</li>
    </ul>

    <h3>Rosemary</h3>
    <ul>
        <li>Mediterranean native—likes it dry between waterings</li>
        <li>Needs excellent drainage</li>
        <li>Prefers cooler temperatures (below 80°F)</li>
        <li>Mist occasionally in dry winter homes</li>
    </ul>

    <h3>Thyme</h3>
    <ul>
        <li>Similar to rosemary—let soil dry between waterings</li>
        <li>Needs good air circulation</li>
        <li>Prune after flowering to keep compact</li>
        <li>Can tolerate some shade</li>
    </ul>

    <h2>Transitioning Outdoor Herbs Inside</h2>

    <p>According to <a href="https://www.axios.com/local/twin-cities/2024/09/28/easy-herb-growing-tips" target="_blank" rel="noopener">Axios</a>, "Bring the plants inside before overnight temperatures dip below 55°F." Additional transition tips:</p>

    <ul>
        <li>Check for pests before bringing plants indoors</li>
        <li>Quarantine new plants for 1-2 weeks</li>
        <li>Gradually reduce watering as plants adjust</li>
        <li>Expect some leaf drop—it's normal adjustment</li>
    </ul>

    <h2>Watering Your Indoor Herbs</h2>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Moisture Preference</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Herbs</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Watering Frequency</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Keep Moist</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Basil, Parsley, Chives, Cilantro</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">When top 1" of soil is dry</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Let Dry Between</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Rosemary, Thyme, Oregano, Sage</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">When top 2" of soil is dry</td>
        </tr>
    </table>

    <img src="{images[3]['url']}" alt="{images[3]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[3]['photographer']}</em></p>

    <h2>Harvesting Tips</h2>

    <ul>
        <li><strong>Harvest in the morning:</strong> Oils are most concentrated before the day heats up</li>
        <li><strong>Never take more than 1/3:</strong> Leave enough foliage for the plant to recover</li>
        <li><strong>Harvest from the top:</strong> Encourages bushy, compact growth</li>
        <li><strong>Pinch, don't pull:</strong> Use clean scissors or pinch with fingernails</li>
        <li><strong>Harvest regularly:</strong> Frequent cutting promotes new growth</li>
    </ul>

    <h2>Common Problems & Solutions</h2>

    <h3>Leggy, Stretched Plants</h3>
    <p><strong>Cause:</strong> Not enough light<br>
    <strong>Fix:</strong> Move to brighter location or add grow lights</p>

    <h3>Yellow Leaves</h3>
    <p><strong>Cause:</strong> Overwatering or poor drainage<br>
    <strong>Fix:</strong> Let soil dry out, ensure drainage holes work</p>

    <h3>Brown Leaf Tips</h3>
    <p><strong>Cause:</strong> Low humidity or salt buildup<br>
    <strong>Fix:</strong> Mist plants, flush soil with water monthly</p>

    <h3>Pests (Aphids, Spider Mites)</h3>
    <p><strong>Fix:</strong> Spray with diluted neem oil or insecticidal soap</p>

    <h2>Getting Started: A Simple Setup</h2>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #17a2b8;">
        <strong>🌿 Beginner Indoor Herb Garden Checklist:</strong>
        <ul>
            <li>☐ South-facing windowsill or grow light</li>
            <li>☐ 6" terracotta pots with saucers</li>
            <li>☐ Quality potting mix</li>
            <li>☐ 3-4 easy herbs: basil, mint, chives, parsley</li>
            <li>☐ Watering can with narrow spout</li>
            <li>☐ Small scissors for harvesting</li>
        </ul>
    </div>

    <h2>Final Thoughts</h2>

    <p>With the fresh herbs market exceeding $4 billion globally, there's clearly a demand for these flavorful plants. But growing your own is more rewarding than buying them. Start with just two or three easy herbs, learn their needs, and expand from there. Within weeks, you'll be snipping fresh basil for pasta, mint for tea, and rosemary for roasts—all from your kitchen windowsill.</p>
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
