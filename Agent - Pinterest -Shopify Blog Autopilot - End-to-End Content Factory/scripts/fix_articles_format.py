"""
Fix Articles Format Script
Fixes articles published by batch script to match the Vanilla Extract format:
1. Direct Answer opening paragraph
2. Proper Sources with anchor links
3. Better structured content

Usage: python fix_articles_format.py [article_id]
       python fix_articles_format.py all  # Fix all recent batch articles
"""

import requests
import json
import re
import time
import sys
from datetime import datetime

# ============== CONFIGURATION ==============
SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
API_VERSION = "2025-01"
BLOG_ID = "108441862462"

HEADERS = {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}

BASE_URL = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}"

# ============== DIRECT ANSWERS FOR EACH TOPIC ==============
# Key = topic keyword, Value = direct answer opening
DIRECT_ANSWERS = {
    "citrus cleaner": "To make DIY citrus cleaner, pack orange peels into a glass jar, cover completely with white vinegar, and let it infuse for 2-3 weeks before straining into a spray bottle with a 1:1 ratio of water. This natural all-purpose cleaner costs pennies and works brilliantly on grease, grime, and kitchen surfaces.",
    "homemade soap": "Making soap at home requires combining oils (like olive, coconut, or lard) with lye (sodium hydroxide) and water in precise ratios, then allowing the mixture to cure for 4-6 weeks. The cold process method is safest for beginners and produces gentle, chemical-free bars that last longer than commercial alternatives.",
    "natural fabric dye": "To dye fabric naturally, simmer food scraps like onion skins (golden yellow), avocado pits (pink), turmeric (bright yellow), or black beans (blue) in water for 1-2 hours, strain, and submerge mordant-treated fabric for several hours. Pre-treating fabric with alum or soy milk helps colors last through washing.",
    "growing herbs indoors": "Growing herbs indoors requires at least 6 hours of bright light daily (south-facing window or grow lights), well-draining potting mix, and consistent watering when the top inch of soil feels dry. Start with easy herbs like basil, mint, chives, and parsley for year-round fresh flavor.",
    "composting": "Start apartment composting with a bokashi bin or small worm bin that fits under your sink. Add kitchen scraps daily, avoid meat and dairy, maintain moisture like a wrung-out sponge, and harvest finished compost every 2-3 months for houseplants or balcony gardens.",
    "beeswax wraps": "Make beeswax wraps by grating 1oz of beeswax onto a 10x10 inch cotton fabric square, melting in a 200°F oven for 5-8 minutes, then lifting and waving to set. These reusable food wraps replace plastic wrap, last up to a year, and are completely compostable at end of life.",
    "preserving lemons": "Preserved lemons are made by quartering lemons (leaving them attached at one end), packing with kosher salt, and pressing into a jar until juices cover them completely. They cure in 3-4 weeks at room temperature, transforming into the tangy, umami-rich ingredient essential to Moroccan cuisine.",
    "fruit leather": "Make fruit leather by pureeing 4 cups of fresh or frozen fruit with 2 tablespoons of honey, spreading 1/8 inch thick on a parchment-lined baking sheet, and dehydrating at 170°F for 6-8 hours until tacky but not sticky. Roll in parchment for storage at room temperature.",
    "seed saving": "Save seeds by harvesting fully mature, open-pollinated vegetables, drying them completely for 1-2 weeks, and storing in labeled paper envelopes in a cool, dark location. Tomatoes and peppers require fermentation, while beans and peas can be collected directly from dried pods.",
    "upcycling clothes": "Transform old clothing by cutting worn jeans into shorts, turning t-shirts into tote bags with simple straight stitches, or patching holes with decorative visible mending. No sewing machine needed—hand stitching works perfectly and adds character to upcycled garments.",
    "natural air freshener": "Create natural air fresheners by simmering citrus peels, cinnamon sticks, and herbs in water on the stovetop, or fill small jars with baking soda and essential oils for odor absorption. Reed diffusers using carrier oil and essential oils provide long-lasting fragrance without synthetic chemicals.",
    "rainwater harvesting": "Set up rainwater harvesting by placing food-grade barrels with mesh screens under your downspouts, installing an overflow pipe, and adding a spigot near the bottom. One inch of rain on a 1,000 sq ft roof yields 600 gallons—plenty for garden irrigation.",
    "fire cider": "Make fire cider by packing a quart jar with chopped onions, garlic, horseradish, ginger, and hot peppers, covering with raw apple cider vinegar, and steeping for 4-6 weeks. Strain and sweeten with honey for a potent immune-boosting tonic taken by the tablespoon.",
    "mushroom growing": "Grow mushrooms at home using sawdust or straw substrate inoculated with spawn, kept in humid conditions (80-90% humidity) with indirect light at 55-75°F. Oyster mushrooms are easiest for beginners, producing first harvests in just 2-3 weeks after pinning.",
    "homemade vinegar": "Make homemade vinegar by combining 1 part raw, unfiltered mother or live vinegar with 3 parts fruit scraps or fruit juice, covering with cloth to allow airflow, and fermenting for 2-4 weeks until acidic. The mother culture can be reused indefinitely for continuous vinegar production.",
    "natural pest control": "Control garden pests naturally by companion planting marigolds (repel aphids), introducing ladybugs, spraying diluted neem oil or soap water on infested plants, and handpicking larger pests at dusk. Healthy soil and plant diversity prevent most pest problems naturally.",
    "herbal tea blend": "Create custom herbal tea blends by combining 2-3 base herbs (chamomile, peppermint, or rooibos) with accent flavors (lavender, lemon balm, rose petals) in a 3:1 ratio. Dry herbs completely before mixing, store in airtight containers away from light, and steep 1 tablespoon per cup for 5-7 minutes.",
    "essential oils": "Use essential oils safely by always diluting in carrier oil (2-3 drops per teaspoon of coconut or jojoba oil), avoiding direct skin contact with undiluted oils, and keeping away from eyes and mucous membranes. Lavender soothes, peppermint energizes, and tea tree disinfects.",
    "natural cleaning products": "Make natural cleaning products using just three ingredients: white vinegar (degreaser and disinfectant), baking soda (gentle abrasive and deodorizer), and castile soap (all-purpose cleaner). Mixed correctly, these replace every chemical cleaner in your home.",
    "fermented vegetables": "Ferment vegetables by submerging them in 2% salt brine (1 tablespoon salt per quart of water), keeping below the liquid with a weight, and storing at room temperature for 3-7 days until tangy. Cabbage becomes sauerkraut, cucumbers become pickles, and any vegetable can be preserved this way.",
    "homemade granola": "Make homemade granola by mixing 3 cups rolled oats with 1/2 cup each nuts and seeds, 1/3 cup oil and maple syrup, a pinch of salt, and baking at 325°F for 25-30 minutes, stirring halfway. Add dried fruit after cooling for clusters that stay crispy in milk.",
    "solar cooking": "Cook with solar energy using a box cooker (cardboard box lined with foil, covered with glass) positioned to catch direct sunlight, reaching temperatures of 250-300°F. Simple dishes like rice, beans, and stews cook perfectly in 2-4 hours of strong sunlight.",
    "home energy": "Reduce home energy consumption by sealing air leaks with weatherstripping, adding programmable thermostats, switching to LED bulbs, and unplugging devices when not in use. These simple changes can cut energy bills by 20-30% with minimal upfront cost.",
    "grey water": "Reuse grey water by redirecting sink, shower, and laundry water (not toilet) to landscape plants through simple gravity-fed systems. Use only biodegradable soaps, avoid grey water on edibles, and alternate with fresh water to prevent soil buildup.",
    "natural cosmetics": "Make natural cosmetics using pantry staples: coconut oil for moisturizer, sugar and olive oil for scrubs, cocoa powder and shea butter for lip balm, and cornstarch with arrowroot for dry shampoo. These recipes work better than commercial products and contain zero synthetic chemicals.",
    "building insect hotels": "Build an insect hotel by stacking wooden pallets, filling cavities with bundled bamboo tubes (cut to 6-8 inches), pinecones, bark, and drilled wood blocks with various hole sizes (2-10mm). Place in a sunny, sheltered spot to attract beneficial pollinators and pest-controlling insects.",
    "bread baking": "Bake basic bread by mixing 500g flour, 325g water, 10g salt, and 7g yeast, kneading until smooth, rising until doubled (1-2 hours), shaping, and baking at 450°F with steam for 30-35 minutes. Sourdough replaces commercial yeast with wild fermentation for deeper flavor.",
    "food waste": "Reduce food waste by planning meals before shopping, organizing refrigerator with oldest items in front, freezing items before spoilage, and repurposing scraps into stock, smoothies, or compost. The average household can save $1,500 annually by preventing food waste.",
    "natural laundry": "Make natural laundry detergent by mixing 1 cup washing soda, 1 cup borax, and 1 bar grated castile soap. Use 2 tablespoons per load. Add white vinegar to the rinse cycle for softening, and wool dryer balls with essential oils to replace dryer sheets.",
    "dehydrating foods": "Dehydrate foods by slicing uniformly thin (1/8-1/4 inch), arranging without overlap on dehydrator trays or oven racks, and drying at 125-135°F until leathery (fruits) or brittle (vegetables). Store in airtight containers with oxygen absorbers for 1+ year shelf life.",
    "natural candle": "Make natural candles by melting soy wax or beeswax, adding 1oz fragrance oil per pound of wax at 185°F, securing a cotton wick in your container, and pouring at 135°F. Allow 24 hours to cure before burning, and trim wicks to 1/4 inch for clean burns.",
    "meal planning": "Plan meals weekly by checking pantry inventory first, building meals around sale items and seasonal produce, prepping ingredients on weekends, and cooking extra portions for repurposed lunches. This system cuts grocery spending by 25% while eliminating the 'what's for dinner' stress.",
    "eco-friendly gift": "Create eco-friendly gifts using mason jars (filled with layered cookie mix, homemade preserves, or bath salts), fabric wrapping instead of paper, potted herbs or seedlings, beeswax wraps, and homemade vanilla extract. Personal, sustainable gifts cost less and mean more.",
    "water conservation": "Conserve water by installing low-flow showerheads (saves 2,700 gallons/year), fixing leaky faucets immediately (each drip wastes 3,000 gallons/year), collecting shower warm-up water for plants, and mulching garden beds to reduce evaporation by 70%.",
    "sustainable shopping": "Shop sustainably by bringing reusable bags, choosing products with minimal packaging, buying in bulk to reduce container waste, supporting local producers at farmers markets, and selecting items with recycled content. Every purchase is a vote for the world you want.",
    "natural remedies": "Create natural remedies using ginger tea for nausea, honey and lemon for sore throats, peppermint oil for headaches, and chamomile for sleep. These time-tested solutions address minor ailments safely when used appropriately and aren't meant to replace professional medical care.",
    "DIY household cleaner": "Make all-purpose cleaner by combining equal parts white vinegar and water with 10 drops essential oil in a spray bottle. For tough jobs, paste baking soda with water, apply, spray with vinegar, and scrub. This $2 solution replaces dozens of specialized cleaners.",
    "repurposing food containers": "Repurpose food containers by washing glass jars for bulk food storage, pantry organization, and homemade gifts. Plastic takeout containers become seedling starters, and cardboard egg cartons work perfectly for fire starters (fill with dryer lint and wax).",
    "natural first aid": "Stock a natural first aid kit with raw honey (wound healing), aloe vera gel (burns), tea tree oil (antiseptic), arnica cream (bruises), activated charcoal (poisoning), and lavender oil (calming). These evidence-backed remedies handle minor injuries without synthetic chemicals.",
    "fermented hot sauce": "Make fermented hot sauce by blending fresh peppers with 2% salt by weight, fermenting in a jar with an airlock for 1-4 weeks, then blending smooth with vinegar to taste. Fermentation develops complex flavors impossible to achieve in cooked hot sauces.",
    "zero-waste broth": "Make zero-waste vegetable broth by freezing vegetable scraps (onion ends, carrot peels, celery leaves, herb stems) until you have 4 cups, simmering in 8 cups water for 1 hour, and straining. This free broth tastes better than store-bought and rescues food from the compost.",
    "vanilla extract": "To make homemade vanilla extract, split 3-5 vanilla beans lengthwise and submerge them in 8 ounces of 80-proof alcohol (vodka, bourbon, or rum), then store in a cool dark place for 2-6 months, shaking weekly. This simple two-ingredient recipe produces extract far superior to most store-bought options.",
}


def get_direct_answer(title):
    """Find the best direct answer for an article title"""
    title_lower = title.lower()

    for keyword, answer in DIRECT_ANSWERS.items():
        if keyword in title_lower:
            return answer

    # Generic fallback with the title
    return f"This comprehensive guide on {title.lower()} provides everything you need to get started with this sustainable practice that's gaining popularity among eco-conscious homemakers."


def detect_batch_article(body_html):
    """Detect if article was created by batch script (has generic opening)"""
    generic_patterns = [
        "Welcome to our comprehensive guide on",
        "This sustainable living practice has been gaining popularity",
        "Whether you're a complete beginner or looking to refine",
    ]

    for pattern in generic_patterns:
        if pattern in body_html:
            return True
    return False


def fix_opening_paragraph(body_html, title):
    """Replace generic opening with direct answer"""
    direct_answer = get_direct_answer(title)

    # Pattern to match the generic opening paragraphs
    patterns = [
        r"<p>Welcome to our comprehensive guide on.*?</p>\s*<p>Whether you\'re a complete beginner.*?</p>",
        r"<p>Welcome to our comprehensive guide on[^<]+</p>",
    ]

    new_opening = f"""<p>{direct_answer}</p>

<p>This guide covers everything you need to know, from essential supplies and step-by-step instructions to troubleshooting tips and creative variations. Whether you're a complete beginner or looking to refine your technique, you'll find practical advice that actually works.</p>"""

    for pattern in patterns:
        if re.search(pattern, body_html, re.DOTALL):
            body_html = re.sub(
                pattern, new_opening, body_html, count=1, flags=re.DOTALL
            )
            return body_html

    return body_html


def fix_sources_section(body_html):
    """Fix sources section to use proper anchor links"""
    # Pattern to find sources with raw URLs
    raw_url_pattern = r"<li>([^<]+)\s*[-–—]\s*(https?://[^<]+)</li>"

    def replace_with_anchor(match):
        name = match.group(1).strip()
        url = match.group(2).strip()
        return f'<li><a href="{url}" target="_blank" rel="noopener">{name}</a></li>'

    return re.sub(raw_url_pattern, replace_with_anchor, body_html)


def get_article(article_id):
    """Fetch article by ID"""
    url = f"{BASE_URL}/blogs/{BLOG_ID}/articles/{article_id}.json"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("article")
    return None


def update_article(article_id, body_html):
    """Update article with new body HTML"""
    url = f"{BASE_URL}/blogs/{BLOG_ID}/articles/{article_id}.json"

    payload = {"article": {"id": article_id, "body_html": body_html}}

    response = requests.put(url, headers=HEADERS, json=payload)
    return response.status_code == 200, response


def get_recent_articles(limit=50):
    """Get recent articles"""
    url = f"{BASE_URL}/blogs/{BLOG_ID}/articles.json?limit={limit}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("articles", [])
    return []


def fix_article(article_id):
    """Fix a single article"""
    print(f"\n📝 Processing article ID: {article_id}")

    article = get_article(article_id)
    if not article:
        print(f"   ❌ Article not found")
        return False

    title = article["title"]
    body_html = article["body_html"]

    print(f"   Title: {title}")

    # Check if it's a batch article
    is_batch = detect_batch_article(body_html)
    print(f"   Is batch article: {is_batch}")

    # Apply fixes
    original_html = body_html

    # Fix 1: Opening paragraph
    if is_batch:
        body_html = fix_opening_paragraph(body_html, title)
        print(f"   ✓ Fixed opening paragraph")

    # Fix 2: Sources section
    body_html = fix_sources_section(body_html)

    # Check if anything changed
    if body_html == original_html:
        print(f"   ⏭ No changes needed")
        return True

    # Update article
    success, response = update_article(article_id, body_html)

    if success:
        print(f"   ✅ Article updated successfully!")
        return True
    else:
        print(f"   ❌ Update failed: {response.status_code}")
        print(f"   {response.text[:200]}")
        return False


def fix_all_batch_articles():
    """Find and fix all batch-generated articles"""
    print("\n" + "=" * 60)
    print("🔧 FIXING BATCH ARTICLES")
    print("=" * 60)

    articles = get_recent_articles(50)
    print(f"\n📊 Found {len(articles)} recent articles")

    fixed_count = 0
    skipped_count = 0

    for article in articles:
        article_id = article["id"]
        title = article["title"]
        body_html = article.get("body_html", "")

        # Only fix batch articles
        if detect_batch_article(body_html):
            if fix_article(article_id):
                fixed_count += 1
            time.sleep(0.5)  # Rate limiting
        else:
            print(f"\n⏭ Skipping: {title[:50]}... (not a batch article)")
            skipped_count += 1

    print("\n" + "=" * 60)
    print(f"✅ COMPLETE: Fixed {fixed_count} articles, skipped {skipped_count}")
    print("=" * 60)


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "all":
            fix_all_batch_articles()
        else:
            try:
                article_id = int(arg)
                fix_article(article_id)
            except ValueError:
                print(f"Invalid argument: {arg}")
                print("Usage: python fix_articles_format.py [article_id | all]")
    else:
        # Default: fix all batch articles
        fix_all_batch_articles()


if __name__ == "__main__":
    main()
