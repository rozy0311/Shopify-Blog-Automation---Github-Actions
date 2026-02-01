#!/usr/bin/env python3
"""
Topic 32: DIY Herbal Salves and Balms
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
        "herbal salve balm natural",
        "calendula flowers dried herbs",
        "beeswax natural skincare",
        "lavender essential oil aromatherapy",
    ]
    images = get_pexels_images(image_queries)

    # Default images if API fails
    while len(images) < 4:
        images.append(
            {
                "url": "https://images.pexels.com/photos/3735149/pexels-photo-3735149.jpeg",
                "alt": "Natural herbal salve",
                "photographer": "Pexels",
            }
        )

    # Article content with real research
    article_html = f"""
<div class="blog-post-content">
    <img src="{images[0]['url']}" alt="{images[0]['alt']}" style="width:100%; max-width:800px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[0]['photographer']}</em></p>

    <p>There's something deeply satisfying about creating your own healing salves from herbs you've grown or foraged yourself. This ancient practice connects us to generations of herbalists while giving us control over exactly what goes on our skin. According to <a href="https://www.usdanalytics.com/industry-reports/herbal-cosmetics-market" target="_blank" rel="noopener">USD Analytics</a>, the <strong>global herbal cosmetics market is valued at $99.1 billion in 2025</strong> and is projected to reach $188.4 billion, growing at a 7.4% CAGR—proof that consumers are increasingly seeking natural alternatives to synthetic skincare.</p>

    <h2>What Is a Herbal Salve?</h2>

    <p>According to <a href="https://bellgardentn.org/making-herbal-salves-at-home/" target="_blank" rel="noopener">BELL Garden</a>, "a salve is a versatile ointment applied to the surface of the body. It can be used to help heal small wounds, moisturize the skin, soothe aches and joints and can even be used as a lip balm."</p>

    <p>Unlike lotions, salves contain no water—they're made purely from oils and beeswax. This creates a waterproof barrier over the skin that helps "force the goodness of the oils into the places you are trying to heal."</p>

    <h3>Salves vs. Balms vs. Ointments</h3>
    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Type</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Consistency</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Best For</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Salve</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Firm, waxy</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Targeted application on wounds, cuts, dry patches</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Balm</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Softer, more spreadable</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Lips, larger areas, massage</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Ointment</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Very soft, almost liquid</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Moisturizing, body application</td>
        </tr>
    </table>

    <h2>The Science Behind Healing Herbs</h2>

    <img src="{images[1]['url']}" alt="{images[1]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[1]['photographer']}</em></p>

    <h3>Calendula: The Skin Healer</h3>
    <p>Research published in <a href="https://www.mdpi.com/2079-9284/8/2/31" target="_blank" rel="noopener">MDPI Cosmetics journal</a> confirms that calendula flower extract has significant anti-inflammatory properties. The study found that "considering calendula's antioxidant, anti-inflammatory and wound healing activity, especially its ability for inhibiting NO production, the topical application of the flower extract is useful both for protecting the skin from sunburn and for ameliorating its symptoms."</p>

    <p>According to <a href="https://www.herbalgram.org/resources/herbclip/issues/2023/issue-717/calendula-leaves-and-flowers-wounds/" target="_blank" rel="noopener">HerbalGram</a>, "in vivo studies showed beneficial anti-inflammatory effects on healing and soothing wounds with topical application of calendula oil at concentrations of 3, 5, and 7%."</p>

    <h3>Other Healing Herbs for Salves</h3>
    <ul>
        <li><strong>Comfrey leaf:</strong> A powerful wound healer containing allantoin, saponins, and polysaccharides. According to Lovely Greens, it "has the ability to treat bruises, sprains, pulled muscles, and other musculature and tissue damage."</li>
        <li><strong>Plantain:</strong> A common "weed" that's excellent for insect bites, stings, and minor skin irritations</li>
        <li><strong>Lavender:</strong> Anti-inflammatory and calming, best known for its soothing properties</li>
        <li><strong>Tea tree:</strong> Strong antiseptic properties</li>
        <li><strong>Chamomile:</strong> Gentle anti-inflammatory perfect for sensitive skin</li>
    </ul>

    <blockquote>
        <p>"Calendula flowers are an anti-inflammatory and antiseptic, which helps soothe sore muscles and treat scrapes and bruises. Lavender is also anti-inflammatory and helps with wounds, but is best known for its calming properties."</p>
        <cite>— BELL Garden</cite>
    </blockquote>

    <h2>Step 1: Making Herb-Infused Oil</h2>

    <p>The foundation of any good salve is herb-infused oil. According to <a href="https://lovelygreens.com/gardeners-healing-salve-recipe-diy-instructions/" target="_blank" rel="noopener">Lovely Greens</a>, you should "begin making the infused oil at least four weeks before making the salve."</p>

    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>Cold Infusion Method (Best Quality)</strong>
        <ol>
            <li><strong>Prepare herbs:</strong> Use fully dried herbs to prevent mold. Any moisture can impact shelf-life.</li>
            <li><strong>Fill jar:</strong> Loosely fill a pint-sized jar half-full with dried herbs</li>
            <li><strong>Add oil:</strong> Pour carrier oil (sweet almond, olive, or coconut) over herbs up to 1/4-inch from top</li>
            <li><strong>Store properly:</strong> Seal, shake, and place in a warm spot out of direct sunlight. If using a windowsill, put jar in a paper bag to protect from UV light</li>
            <li><strong>Shake daily:</strong> Give the jar a gentle shake each day</li>
            <li><strong>Strain:</strong> After 3-6 weeks, strain through cheesecloth. Store infused oil in a clean jar.</li>
        </ol>
        <p><em>Shelf life: Up to 1 year when stored in a dim place at room temperature</em></p>
    </div>

    <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #ffc107;">
        <strong>Quick Heat Infusion Method (Same Day)</strong>
        <ol>
            <li>Place dried herbs and oil in a double boiler</li>
            <li>Heat on low for 2-4 hours, stirring occasionally</li>
            <li>Strain while still warm through cheesecloth</li>
            <li>Allow to cool before storing</li>
        </ol>
        <p><em>Note: Lower quality but useful when you need infused oil quickly</em></p>
    </div>

    <h2>Step 2: The Magic Ratio</h2>

    <img src="{images[2]['url']}" alt="{images[2]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[2]['photographer']}</em></p>

    <p>According to <a href="https://gardenchick.com/diy-herbal-salve-soothing-lavender-cooling-peppermint-and-antiseptic-tea-tree/" target="_blank" rel="noopener">Garden Chick</a>, the oil-to-beeswax ratio determines your salve's consistency:</p>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Ratio (Oil:Beeswax)</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Consistency</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Best For</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>3:1</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Hard/Firm</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Lip balms, hot climates</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>4:1</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Medium/Standard</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">All-purpose healing salve</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>5:1</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Soft/Spreadable</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Body balms, massage</td>
        </tr>
    </table>

    <h2>Basic Healing Salve Recipe</h2>

    <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #28a745;">
        <strong>Gardener's Healing Salve</strong>
        <p><em>From Tanya Anderson, Lovely Greens</em></p>

        <strong>Ingredients:</strong>
        <ul>
            <li>4 oz (120ml) herb-infused oil (calendula, plantain, and/or comfrey)</li>
            <li>1 oz (28g) beeswax pellets</li>
            <li>Optional: 10-15 drops essential oil</li>
        </ul>

        <strong>Instructions:</strong>
        <ol>
            <li>Fill a large pan with water and bring to a boil</li>
            <li>Measure beeswax into a smaller pan and float it inside the pan of boiling water (never melt beeswax over direct heat)</li>
            <li>When beeswax is melted, pour in the herb-infused oil</li>
            <li>Stir with a spatula until oils are just melted</li>
            <li>Remove from heat and let cool slightly (if adding essential oils, add now)</li>
            <li>Pour into tins or containers</li>
            <li>Allow to cool 4+ hours—don't cover until completely cooled to prevent condensation</li>
        </ol>

        <p><em>Shelf life: Up to 1 year</em></p>
    </div>

    <h2>Specialized Salve Recipes</h2>

    <h3>Soothing Lavender, Cooling Peppermint & Antiseptic Tea Tree Salve</h3>
    <p>From <a href="https://gardenchick.com/diy-herbal-salve-soothing-lavender-cooling-peppermint-and-antiseptic-tea-tree/" target="_blank" rel="noopener">Garden Chick</a>:</p>
    <ul>
        <li>4 oz infused calendula oil</li>
        <li>1 oz beeswax</li>
        <li>10-12 drops lavender essential oil</li>
        <li>6-8 drops peppermint essential oil</li>
        <li>4-6 drops tea tree essential oil</li>
    </ul>

    <h3>Simple Muscle Rub</h3>
    <ul>
        <li>4 oz comfrey-infused oil</li>
        <li>1 oz beeswax</li>
        <li>15 drops eucalyptus essential oil</li>
        <li>10 drops peppermint essential oil</li>
        <li>5 drops rosemary essential oil</li>
    </ul>

    <img src="{images[3]['url']}" alt="{images[3]['alt']}" style="width:100%; max-width:700px; height:auto; margin: 20px 0; border-radius: 8px;">
    <p><em>Photo by {images[3]['photographer']}</em></p>

    <h2>Choosing the Right Carrier Oil</h2>

    <table style="width:100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background: #e9ecef;">
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Oil</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Properties</th>
            <th style="padding: 12px; text-align: left; border: 1px solid #dee2e6;">Best For</th>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Sweet Almond</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Light, absorbs well, mild scent</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">All-purpose salves, sensitive skin</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Olive Oil</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Rich, moisturizing, long shelf life</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Healing salves, very dry skin</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Coconut Oil</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Antimicrobial, solid at room temp</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Wound healing, antibacterial salves</td>
        </tr>
        <tr>
            <td style="padding: 12px; border: 1px solid #dee2e6;"><strong>Jojoba Oil</strong></td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Similar to skin's sebum, very stable</td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">Face balms, acne-prone skin</td>
        </tr>
    </table>

    <h2>Essential Safety Tips</h2>

    <ul>
        <li><strong>Patch test first:</strong> "Always remember to perform a patch test before applying any essential oil blend to a larger area of your body," advises Garden Chick</li>
        <li><strong>Never apply undiluted essential oils:</strong> Essential oils should always be mixed with a carrier oil</li>
        <li><strong>Avoid comfrey root:</strong> According to Lovely Greens, you should "avoid using comfrey root, rich in the pyrrolizidine alkaloids that are so troublesome"—the leaf is safe for topical use</li>
        <li><strong>Avoid deep wounds:</strong> Don't apply salves directly on deep cuts; smooth around the injured area</li>
        <li><strong>Ensure herbs are fully dry:</strong> Any moisture can cause mold and spoil your salve</li>
        <li><strong>Store properly:</strong> Keep in cool, dark place. Refrigerate in hot climates.</li>
    </ul>

    <blockquote>
        <p>"The finished herbal healing salve is good for occasional bumps, burns, rashes, and bruises. It's perfect for dry skin and nails, tiny cuts and scrapes, and softening rough patches and calluses."</p>
        <cite>— Tanya Anderson, Lovely Greens</cite>
    </blockquote>

    <h2>Growing Your Own Herbs for Salves</h2>

    <p>Many salve herbs are easy to grow in gardens or containers:</p>
    <ul>
        <li><strong>Calendula:</strong> Annual, easy to grow from seed, blooms prolifically</li>
        <li><strong>Lavender:</strong> Perennial, loves sunny, well-drained soil</li>
        <li><strong>Comfrey:</strong> Perennial, spreads vigorously, harvest leaves throughout season</li>
        <li><strong>Plantain:</strong> Often grows wild in lawns—just ensure area is pesticide-free</li>
        <li><strong>Chamomile:</strong> Annual, self-seeds readily</li>
    </ul>

    <h2>Final Thoughts</h2>

    <p>Making your own herbal salves is a rewarding skill that combines traditional herbal knowledge with practical self-sufficiency. With just a few quality ingredients and some patience for infusing oils, you can create personalized healing products that are free from synthetic chemicals and preservatives.</p>

    <p>Start with a simple calendula salve, master the basic technique, and then experiment with different herbs and essential oil combinations to address specific needs—from muscle aches to chapped winter skin to garden scrapes. Your hands (and your friends who receive these as gifts) will thank you.</p>

    <hr style="margin: 30px 0;">

    <h3>References</h3>
    <ol style="font-size: 0.9em; color: #666;">
        <li>USD Analytics. "Herbal Cosmetics Market Demand and Growth Opportunities 2025." <a href="https://www.usdanalytics.com/industry-reports/herbal-cosmetics-market" target="_blank">usdanalytics.com</a></li>
        <li>BELL Garden. "Making Herbal Salves At Home." December 2019. <a href="https://bellgardentn.org/making-herbal-salves-at-home/" target="_blank">bellgardentn.org</a></li>
        <li>Creel, Karen. "DIY Herbal Salve: Soothing Lavender, Cooling Peppermint, and Antiseptic Tea Tree." Garden Chick, May 2023. <a href="https://gardenchick.com/diy-herbal-salve-soothing-lavender-cooling-peppermint-and-antiseptic-tea-tree/" target="_blank">gardenchick.com</a></li>
        <li>Anderson, Tanya. "Gardener's Healing Salve Recipe." Lovely Greens. <a href="https://lovelygreens.com/gardeners-healing-salve-recipe-diy-instructions/" target="_blank">lovelygreens.com</a></li>
        <li>MDPI. "Anti-Inflammatory Activity of Calendula officinalis L. Flower Extract." Cosmetics 2021, 8, 31. <a href="https://www.mdpi.com/2079-9284/8/2/31" target="_blank">mdpi.com</a></li>
        <li>HerbalGram. "Extracts of Calendula Leaves and Flowers Offer Wound-healing Properties." Issue 717, 2023. <a href="https://www.herbalgram.org/resources/herbclip/issues/2023/issue-717/calendula-leaves-and-flowers-wounds/" target="_blank">herbalgram.org</a></li>
    </ol>
</div>
"""

    # Prepare article data
    article_data = {
        "article": {
            "title": "DIY Herbal Salves and Balms: A Complete Guide to Natural Skin Healing",
            "author": "The Rike",
            "body_html": article_html,
            "tags": "herbal salves, DIY balms, calendula salve, natural skincare, beeswax recipes, herb infused oil, sustainable living, homemade remedies",
            "published": True,
            "metafields": [
                {
                    "namespace": "global",
                    "key": "title_tag",
                    "value": "DIY Herbal Salves and Balms: Complete Guide to Natural Skin Healing",
                    "type": "single_line_text_field",
                },
                {
                    "namespace": "global",
                    "key": "description_tag",
                    "value": "Learn to make healing herbal salves and balms with calendula, lavender, and comfrey. Step-by-step recipes for natural skincare using beeswax and infused oils.",
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

    print("Publishing article: DIY Herbal Salves and Balms...")
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
