#!/usr/bin/env python3
"""
Topic 27: Seed Saving for Beginners
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

    images = get_pexels_images("seeds garden vegetables tomato", 4)
    if len(images) < 4:
        images += get_pexels_images("garden harvest seeds save", 4 - len(images))

    default_images = [
        "https://images.pexels.com/photos/1105019/pexels-photo-1105019.jpeg",
        "https://images.pexels.com/photos/2286921/pexels-photo-2286921.jpeg",
        "https://images.pexels.com/photos/169523/pexels-photo-169523.jpeg",
        "https://images.pexels.com/photos/1084540/pexels-photo-1084540.jpeg",
    ]
    images = images if len(images) >= 4 else default_images

    html_content = f"""
<article class="blog-article seed-saving">

<p class="intro"><strong>Seed saving connects gardeners to an ancient practice that ensures food security, preserves genetic diversity, and saves money season after season.</strong> According to <a href="https://mordorintelligence.com" target="_blank" rel="noopener">Mordor Intelligence</a>, open-pollinated varieties account for <strong>40.5% of the U.S. garden seeds market in 2024</strong>—seeds that allow gardeners to save and replant, adapting plant lines to local conditions while providing long-term cost efficiency.</p>

<img src="{images[0]}" alt="Seeds ready for saving from garden vegetables" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Why Save Seeds?</h2>

<p>The global heirloom seed subscription market reached <strong>$1.42 billion in 2024</strong>, driven by growing interest in sustainable agriculture and home gardening. This market is expected to reach <strong>$2.98 billion by 2033</strong> with an 8.9% CAGR, according to Growth Market Reports. The surge reflects consumer awareness of biodiversity, food security, and the nutritional benefits of heirloom varieties.</p>

<h3>Benefits of Seed Saving</h3>

<ul>
<li><strong>Cost savings:</strong> One tomato can yield dozens of seeds—enough for years of planting</li>
<li><strong>Local adaptation:</strong> Plants gradually adapt to your specific climate and soil conditions</li>
<li><strong>Biodiversity preservation:</strong> Contributing to genetic diversity essential for food security</li>
<li><strong>Self-sufficiency:</strong> Reducing dependence on commercial seed sources</li>
<li><strong>Connection to heritage:</strong> Preserving varieties with historical and cultural significance</li>
</ul>

<blockquote>
<p>"Open-pollinated varieties allow gardeners to save seeds and adapt plant lines to local conditions, providing long-term cost efficiency. Their contribution to biodiversity conservation and self-sufficiency adds to their appeal among gardeners."</p>
<footer>— <cite>Mordor Intelligence, U.S. Garden Seeds Market Analysis 2024</cite></footer>
</blockquote>

<img src="{images[1]}" alt="Heirloom tomatoes for seed saving" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Understanding Seed Types</h2>

<h3>Open-Pollinated vs. Hybrid</h3>

<table style="width:100%;border-collapse:collapse;margin:20px 0;">
<thead>
<tr style="background:#f8f9fa;">
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Seed Type</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Can You Save?</th>
<th style="padding:12px;text-align:left;border:1px solid #ddd;">Characteristics</th>
</tr>
</thead>
<tbody>
<tr>
<td style="padding:12px;border:1px solid #ddd;"><strong>Open-Pollinated</strong></td>
<td style="padding:12px;border:1px solid #ddd;">✅ Yes</td>
<td style="padding:12px;border:1px solid #ddd;">Seeds produce plants true to parent; can be saved and replanted</td>
</tr>
<tr style="background:#f8f9fa;">
<td style="padding:12px;border:1px solid #ddd;"><strong>Heirloom</strong></td>
<td style="padding:12px;border:1px solid #ddd;">✅ Yes</td>
<td style="padding:12px;border:1px solid #ddd;">Open-pollinated varieties passed down 50+ years; unique flavors</td>
</tr>
<tr>
<td style="padding:12px;border:1px solid #ddd;"><strong>Hybrid (F1)</strong></td>
<td style="padding:12px;border:1px solid #ddd;">❌ Not reliable</td>
<td style="padding:12px;border:1px solid #ddd;">Cross between two varieties; seeds won't produce same plant</td>
</tr>
</tbody>
</table>

<div class="tip-box" style="background:#fff3cd;padding:20px;border-radius:12px;margin:20px 0;border-left:4px solid #ffc107;">
<h4>💡 Key Insight</h4>
<p>According to Mordor Intelligence, while hybrid seeds "maintain their market position due to consistent size, enhanced disease resistance, and higher yields," open-pollinated seeds are essential for seed saving. Look for "OP" (open-pollinated) or "Heirloom" labels when purchasing seeds you plan to save.</p>
</div>

<h2>Best Beginner Seeds to Save</h2>

<p>According to <a href="https://homesteadingfamily.com" target="_blank" rel="noopener">Homesteading Family</a>, "Tomato, cucumber, corn, and peas are a great place to begin seed saving so you can plant your own seed next year." These vegetables are self-pollinating or easy to isolate, making them perfect for beginners.</p>

<img src="{images[2]}" alt="Garden vegetables ready for seed saving" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h3>1. Tomatoes (Easiest)</h3>

<p>As noted in <a href="https://rootsandrefuge.com" target="_blank" rel="noopener">Roots and Refuge's Complete Guide</a>:</p>

<ol>
<li><strong>Choose:</strong> Select a good quality, fully ripe tomato</li>
<li><strong>Scoop:</strong> Use a spoon to scoop seeds and gel into a small mason jar</li>
<li><strong>Ferment:</strong> Fill jar with water and let sit 2-3 days until mold forms (this removes germination-inhibiting gel)</li>
<li><strong>Rinse:</strong> Pour off mold, rinse seeds in a fine sieve</li>
<li><strong>Dry:</strong> Spread on paper towels and dry completely (1-2 weeks)</li>
</ol>

<h3>2. Peppers</h3>

<p>Even simpler than tomatoes! One gardener shares: "I hope this gives you some idea of how to save pepper seed and tomato seeds—it's really, really easy to do. I highly recommend it; it will save you some money."</p>

<ol>
<li>Choose fully ripe, mature peppers (color should be final stage—red, orange, yellow)</li>
<li>Cut open and scrape out seeds</li>
<li>Spread on paper towels to dry for 1-2 weeks</li>
<li>Store in labeled envelope</li>
</ol>

<h3>3. Beans and Peas</h3>

<ul>
<li>Let pods dry on the vine until brown and rattling</li>
<li>Harvest pods and shell seeds</li>
<li>Dry additional week indoors</li>
<li>Store in airtight container</li>
</ul>

<h3>4. Lettuce and Leafy Greens</h3>

<ul>
<li>Allow plants to "bolt" (flower and go to seed)</li>
<li>Wait for seed heads to dry on plant</li>
<li>Shake seeds into paper bag</li>
<li>Clean and store</li>
</ul>

<img src="{images[3]}" alt="Saved seeds in storage containers" style="width:100%;max-width:800px;border-radius:12px;margin:20px 0;">

<h2>Seed Saving Organizations</h2>

<p>Several organizations lead the movement in preserving open-pollinated and heirloom varieties:</p>

<ul>
<li><strong>Seed Savers Exchange:</strong> Non-profit focusing on conservation and sharing of open-pollinated seeds</li>
<li><strong>Baker Creek Heirloom Seeds:</strong> Renowned for extensive catalog of rare and historic varieties</li>
<li><strong>Southern Exposure Seed Exchange:</strong> Emphasizes regional adaptation and sustainable farming practices</li>
<li><strong>Johnny's Selected Seeds:</strong> Offers trial-backed cultivars and detailed crop guides</li>
</ul>

<blockquote>
<p>"Baker Creek Heirloom Seeds is renowned for its extensive catalog of rare and historic varieties, as well as its commitment to seed preservation and education."</p>
<footer>— <cite>Growth Market Reports</cite></footer>
</blockquote>

<h2>Storage Best Practices</h2>

<div class="info-box" style="background:#e8f4f8;padding:20px;border-radius:12px;margin:20px 0;">
<h4>📦 Proper Seed Storage</h4>
<ul>
<li><strong>Cool and dry:</strong> Store at 40-50°F with low humidity</li>
<li><strong>Airtight containers:</strong> Mason jars with silica gel packets work well</li>
<li><strong>Label everything:</strong> Include variety name, date saved, and any notes</li>
<li><strong>Viable duration:</strong> Most vegetable seeds last 2-5 years when stored properly</li>
<li><strong>Refrigerator or freezer:</strong> Extends viability significantly for long-term storage</li>
</ul>
</div>

<h2>The Growing Movement</h2>

<p>The organic seeds segment demonstrates the highest growth rate at <strong>11.7% CAGR projected through 2030</strong>, with the USDA providing <strong>$2.2 million in educational funding</strong> through the Organic Trade Association. This reflects a fundamental shift in how consumers view food production—from passive consumers to active participants in the food system.</p>

<h2>Start Your Seed-Saving Journey</h2>

<p>Begin with just one or two easy vegetables this season. As you develop confidence, expand to more challenging varieties. Each saved seed represents not just cost savings, but a vote for biodiversity, self-sufficiency, and sustainable gardening practices that benefit both your garden and the planet.</p>

<p><em>Ready to organize your seed collection? Explore our <a href="/collections/storage">sustainable storage solutions</a> perfect for keeping your saved seeds fresh and organized season after season.</em></p>

</article>
"""

    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

    article_data = {
        "article": {
            "title": "Seed Saving for Beginners: A Complete Guide to Growing Food Independence",
            "author": "The Rike",
            "body_html": html_content,
            "tags": "seed-saving,gardening,heirloom-seeds,sustainable-gardening,biodiversity,self-sufficiency,organic-gardening",
            "published": True,
            "image": {
                "src": images[0],
                "alt": "Seeds ready for saving from garden vegetables",
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

        seo_title = "Seed Saving for Beginners | How to Save Tomato & Vegetable Seeds | The Rike"
        seo_desc = "Complete beginner's guide to seed saving. Learn to save tomato, pepper, and bean seeds. Save money, preserve biodiversity, grow food independence."

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
