#!/usr/bin/env python3
"""
Topic 30: Making Natural Air Fresheners
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
        "essential oil diffuser aromatherapy",
        "lavender dried herbs natural",
        "citrus lemon orange fresh",
        "natural home fragrance candles",
    ]
    images = get_pexels_images(image_queries)

    # Default images if API fails
    while len(images) < 4:
        images.append(
            {
                "url": "https://images.pexels.com/photos/4041392/pexels-photo-4041392.jpeg",
                "alt": "Natural air freshener essential oils",
                "photographer": "Pexels",
            }
        )

    # Article content with real research
    article_html = f"""
<div class="blog-post-content">
    <img src="{images[0]['url']}" alt="{images[0]['alt']}" style="width:100%; max-width:800px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[0]['photographer']}</em></p>

    <p>Commercial air fresheners promise to make our homes smell delightful, but they often come with hidden health costs. According to the <strong>MADE SAFE organization</strong>, "air fresheners in many cases do not actually improve air quality by removing impurities—when asked for data to back up their claims, manufacturers were unable to provide public data and information." It's time to explore natural alternatives that genuinely freshen your air without the toxic trade-offs.</p>

    <h2>The Hidden Dangers of Conventional Air Fresheners</h2>

    <p>Before diving into natural alternatives, let's understand why this matters. <strong>The EPA reports that people today spend up to 90% of their time indoors</strong>, making indoor air quality critically important. Yet research shows that synthetic air fresheners contribute significantly to indoor air pollution.</p>

    <p>The <strong>Scientific Committee on Health and Environmental Risks (SCHER)</strong> tested 74 consumer air freshener products sold in Europe and found high concentrations of volatile organic compounds (VOCs) in emissions from numerous air freshener types—including sprays, plug-ins, and solid fresheners. According to <a href="https://madesafe.org/blogs/viewpoint/toxic-chemicals-in-air-fresheners" target="_blank" rel="noopener">MADE SAFE's research</a>, these products can contain:</p>

    <ul>
        <li><strong>Formaldehyde</strong> - a known carcinogen</li>
        <li><strong>Benzene</strong> - linked to cancer and reproductive toxicity</li>
        <li><strong>Phthalates</strong> - associated with endocrine disruption</li>
        <li><strong>1,4-Dichlorobenzene</strong> - a VOC that may impair lung function</li>
    </ul>

    <blockquote>
        <p>"Air freshener chemicals can stick to and be absorbed by furniture, walls and surfaces, carpets, and more. They can then be released and re-enter indoor air even after the air freshener is no longer in use."</p>
        <cite>— Anne Steinemann, Building and Environment, 2016</cite>
    </blockquote>

    <h2>The Science Behind Natural Essential Oils</h2>

    <img src="{images[1]['url']}" alt="{images[1]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[1]['photographer']}</em></p>

    <p>Natural alternatives aren't just "less bad"—they can actually provide genuine benefits. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC8151751/" target="_blank" rel="noopener">Research published in the NIH National Library of Medicine</a> found that tea tree, rosemary, eucalyptus, and lavender essential oils exhibit a broad spectrum of antimicrobial activity.</p>

    <p>Key findings from the scientific study:</p>
    <ul>
        <li><strong>Tea tree oil</strong> demonstrated the strongest antimicrobial activity, effective against E. coli, S. aureus, and other pathogens</li>
        <li><strong>Essential oils reduced viral infectivity by over 96%</strong> in laboratory tests (Astani et al., 2010)</li>
        <li><strong>Lavender oil has anxiolytic effects</strong>, with meta-analyses proving reduction in cortisol levels and improved sleep quality</li>
    </ul>

    <p>According to <strong>market reports, essential oil sales are growing 9-10% annually</strong>, driven by wellness trends and demand for natural immune boosters. The most popular oils for home use include lavender (relaxation), tea tree (disinfection), eucalyptus (respiratory health), and peppermint (energy).</p>

    <h2>DIY Natural Air Freshener Recipes</h2>

    <h3>1. Simple Room Spray (Most Popular)</h3>
    <p>This viral recipe has been shared across homesteading communities for its effectiveness and simplicity:</p>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>Basic Room Spray Recipe:</strong>
        <ul>
            <li>1 cup distilled water</li>
            <li>1 tablespoon baking soda</li>
            <li>10-15 drops essential oil (lavender, lemon, or your choice)</li>
            <li>Spray bottle</li>
        </ul>
        <p><em>Directions: Mix baking soda into water until dissolved. Add essential oils. Shake well before each use. Spray into the air, avoiding fabrics and wood surfaces.</em></p>
    </div>

    <h3>2. Baking Soda Odor Absorber</h3>
    <p>Unlike synthetic fresheners that mask odors, baking soda actually neutralizes them:</p>
    <ul>
        <li>1/2 cup baking soda</li>
        <li>10-15 drops essential oil</li>
        <li>Mason jar with lid (poke holes in lid or use fabric cover)</li>
    </ul>
    <p>Place in closets, bathrooms, or near trash cans. Replace monthly.</p>

    <img src="{images[2]['url']}" alt="{images[2]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[2]['photographer']}</em></p>

    <h3>3. Stovetop Potpourri (Seasonal Favorite)</h3>
    <p>According to <a href="https://www.spendwithpennies.com/homemade-air-fresheners/" target="_blank" rel="noopener">Spend With Pennies</a>, stovetop potpourri is "easy to make your house smell amazing with ingredients you already have on hand."</p>

    <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ffc107;">
        <strong>Classic Citrus & Spice Potpourri:</strong>
        <ul>
            <li>1 orange or lemon, sliced</li>
            <li>2 cinnamon sticks</li>
            <li>1 tablespoon whole cloves</li>
            <li>2 sprigs rosemary or thyme</li>
            <li>Water to cover</li>
        </ul>
        <p><em>Simmer on low heat, adding water as needed. Never leave unattended.</em></p>
    </div>

    <h3>4. Essential Oil Diffuser Blends</h3>
    <p>Using an ultrasonic diffuser is one of the safest ways to disperse essential oils. Popular blends:</p>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Blend Name</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Essential Oils</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Benefits</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Fresh & Clean</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">3 drops lemon + 2 drops tea tree + 2 drops eucalyptus</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Antimicrobial, energizing</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Relaxation</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">4 drops lavender + 2 drops chamomile + 1 drop vanilla</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Stress relief, sleep support</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Forest Walk</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">3 drops pine + 2 drops cedarwood + 2 drops eucalyptus</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Grounding, respiratory</td>
        </tr>
    </table>

    <h3>5. Gel Air Fresheners</h3>
    <p>For continuous fragrance without heat or electricity:</p>
    <ul>
        <li>1 cup water</li>
        <li>2 packets unflavored gelatin</li>
        <li>1 tablespoon salt (as preservative)</li>
        <li>20-30 drops essential oil</li>
        <li>Optional: natural food coloring</li>
    </ul>
    <p>Heat water, dissolve gelatin and salt, add oils, pour into jars. Set for 24 hours.</p>

    <img src="{images[3]['url']}" alt="{images[3]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[3]['photographer']}</em></p>

    <h2>Safety Tips for Natural Air Fresheners</h2>

    <p>While natural options are generally safer, they still require precautions:</p>

    <ul>
        <li><strong>Pet safety:</strong> Some essential oils are toxic to cats and dogs—especially tea tree, peppermint, and citrus oils. Consult your vet before using diffusers around pets.</li>
        <li><strong>Child safety:</strong> Keep essential oils out of reach. Never apply undiluted oils to skin.</li>
        <li><strong>Quality matters:</strong> Look for 100% pure essential oils without synthetic additives. Check for third-party testing.</li>
        <li><strong>Ventilation:</strong> Even natural fragrances can irritate sensitive individuals. Ensure good air circulation.</li>
        <li><strong>Surface caution:</strong> Essential oils can damage certain surfaces. Test in inconspicuous areas first.</li>
    </ul>

    <blockquote>
        <p>"Be wary of 'all natural' and 'green' claims on air fresheners. These marketing tactics have no legal or regulatory status, so remember to dig deeper to ensure the product is truly safe."</p>
        <cite>— MADE SAFE Organization</cite>
    </blockquote>

    <h2>Cost Comparison: DIY vs. Commercial</h2>

    <p>Beyond health benefits, natural air fresheners offer significant savings:</p>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Product</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Commercial Cost</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">DIY Cost</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Annual Savings</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Room Spray (8 oz)</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">$5-8</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">$0.50-1</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">$50-85/year</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Plug-in Refills (monthly)</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">$6-10/month</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">$2-3/month (diffuser oil)</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">$48-84/year</td>
        </tr>
    </table>

    <p>Initial investment in quality essential oils pays off within months, while you gain complete control over ingredients.</p>

    <h2>Where to Source Quality Ingredients</h2>

    <ul>
        <li><strong>Essential oils:</strong> Look for USDA Organic certification, GC/MS testing documentation, and reputable brands</li>
        <li><strong>Dried herbs:</strong> Grow your own lavender, rosemary, and mint, or purchase from farmers markets</li>
        <li><strong>Baking soda:</strong> Available at any grocery store—look for aluminum-free varieties</li>
        <li><strong>Spray bottles:</strong> Choose glass over plastic to prevent oil degradation</li>
    </ul>

    <h2>Final Thoughts</h2>

    <p>Making the switch from commercial air fresheners to natural alternatives isn't just about avoiding toxic chemicals—it's about actively improving your indoor air quality. With scientific evidence supporting the antimicrobial and wellness benefits of essential oils, you're not just masking odors but potentially purifying your air while creating a healthier home environment.</p>

    <p>Start with one simple recipe, like the basic room spray. Once you experience the difference, you'll wonder why you ever relied on synthetic fragrances in the first place.</p>

    <hr style="margin: 30px 0;">

    <h3>References</h3>
    <ol style="font-size: 0.9em; color: #666;">
        <li>MADE SAFE. "Toxic Chemicals in Air Fresheners." January 2020. <a href="https://madesafe.org/blogs/viewpoint/toxic-chemicals-in-air-fresheners" target="_blank">madesafe.org</a></li>
        <li>EPA. "The Inside Story: A Guide to Indoor Air Quality." June 2023. <a href="https://www.epa.gov/indoor-air-quality-iaq/inside-story-guide-indoor-air-quality" target="_blank">epa.gov</a></li>
        <li>NIH National Library of Medicine. "Antimicrobial Activity of Essential Oils." PMC8151751. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC8151751/" target="_blank">pmc.ncbi.nlm.nih.gov</a></li>
        <li>Steinemann, Anne. "Ten Questions Concerning Air Fresheners and Indoor Built Environments." Building and Environment, 2016.</li>
        <li>Scientific Committee on Health and Environmental Risks (SCHER). "Emission of Chemicals by Air Fresheners Tests on 74 Consumer Products Sold in Europe." 2006.</li>
        <li>Astani, A. et al. "Antiviral Activity of Essential Oils." 2010.</li>
    </ol>
</div>
"""

    # Prepare article data
    article_data = {
        "article": {
            "title": "Making Natural Air Fresheners: Safe DIY Recipes for a Toxin-Free Home",
            "author": "The Rike",
            "body_html": article_html,
            "tags": "natural air freshener, homemade room spray, essential oil diffuser, stovetop potpourri, DIY home fragrance, sustainable living, eco-friendly home",
            "published": True,
            "metafields": [
                {
                    "namespace": "global",
                    "key": "title_tag",
                    "value": "Making Natural Air Fresheners: Safe DIY Recipes for a Toxin-Free Home",
                    "type": "single_line_text_field",
                },
                {
                    "namespace": "global",
                    "key": "description_tag",
                    "value": "Learn to make natural air fresheners with essential oils, baking soda, and herbs. Avoid toxic VOCs and synthetic fragrances while creating a healthier home environment.",
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

    print("Publishing article: Making Natural Air Fresheners...")
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
