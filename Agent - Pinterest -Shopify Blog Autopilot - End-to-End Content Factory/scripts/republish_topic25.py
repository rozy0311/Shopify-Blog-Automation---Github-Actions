#!/usr/bin/env python3
"""
Topic 25: Preserved Lemons - Republish with hidden links and researched content
Sources:
- Cultured Guru - Moroccan Salt-Preserved Lemons
- Taste of Maroc - How to Make Preserved Lemons
- USDA - Citrus Fruits 2024 ($2.84 billion US crop)
- Citrus Industry Magazine - Market data
"""

import requests

SHOP = "the-rike-inc.myshopify.com"
TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"

ARTICLE_TITLE = "Preserved Lemons: How to Make This Essential Pantry Staple"

BODY_HTML = """
<p>In the world of home preservation, few ingredients carry as much flavor complexity as preserved lemons. This ancient Moroccan technique transforms ordinary citrus into an intensely flavored condiment that can elevate dishes for months to come. With the <a href="https://esmis.nal.usda.gov/sites/default/release-files/j9602060k/vx023d76b/w9507070x/cfrt0825.pdf" target="_blank" rel="noopener">USDA reporting</a> the U.S. citrus crop valued at $2.84 billion, there's no shortage of lemons to experiment with this traditional preservation method.</p>

<h2>Why Preserved Lemons Are a Kitchen Essential</h2>

<p>Unlike fresh lemons, preserved lemons undergo a transformation through salt-curing that concentrates their flavor while mellowing the bitter notes. The <a href="https://cultured.guru/blog/how-to-make-moroccan-salt-preserved-lemons" target="_blank" rel="noopener">Cultured Guru</a> explains that according to Toby Sonneman's "Lemon: A Global History," the traditional recipe calls for "slitting the fruit and filling the gashes with salt, then pressing them into a jar, covering with lemon juice and letting them ferment for weeks."</p>

<p>This simple technique creates a pantry staple that:</p>
<ul>
  <li>Adds bright, complex citrus flavor to tagines and stews</li>
  <li>Elevates simple grain dishes and salads</li>
  <li>Transforms marinades and dressings</li>
  <li>Lasts for months (even years) in your refrigerator</li>
</ul>

<h2>What You'll Need</h2>

<p>According to <a href="https://tasteofmaroc.com/how-to-make-preserved-lemons/" target="_blank" rel="noopener">Taste of Maroc</a>, "Two simple ingredients and a few minutes of your time are all that's needed to make homemade preserved lemons."</p>

<h3>Basic Ingredients:</h3>
<ul>
  <li>6-8 organic lemons (Meyer lemons work exceptionally well)</li>
  <li>1/2 cup coarse sea salt or kosher salt</li>
  <li>Additional lemon juice (about 1 cup)</li>
  <li>Optional: cinnamon stick, bay leaves, or peppercorns</li>
</ul>

<h3>Equipment:</h3>
<ul>
  <li>1 quart glass jar with tight-fitting lid</li>
  <li>Sterilized jar (run through dishwasher or boil)</li>
</ul>

<h2>Step-by-Step Preservation Process</h2>

<h3>Step 1: Prepare the Lemons</h3>
<p>Scrub lemons thoroughly under running water to remove any wax coating. Cut off the stem end, then quarter the lemon from the top, stopping about 1/2 inch from the bottom so the lemon stays connected.</p>

<h3>Step 2: Pack with Salt</h3>
<p>Open each quartered lemon and generously pack 1-2 tablespoons of salt into the cuts. The salt is what preserves the lemons and draws out the natural juices to create the brine.</p>

<h3>Step 3: Fill the Jar</h3>
<p>Place a layer of salt at the bottom of your sterilized jar. Pack the salted lemons tightly into the jar, pressing down firmly to release their juices. Add more salt between layers. The key is pressing firmly—you want the lemons completely submerged in their own juice.</p>

<h3>Step 4: Top and Seal</h3>
<p>If the lemon juice doesn't cover the fruit completely, add fresh-squeezed lemon juice until everything is submerged. Seal the jar tightly.</p>

<h3>Step 5: Cure Time</h3>
<p>Store at room temperature for 3-4 weeks, turning or shaking the jar every day or two. The lemons are ready when the rinds are soft and the liquid becomes syrupy. Once opened, refrigerate and they'll last up to a year.</p>

<h2>Tips for Perfect Preserved Lemons</h2>

<ul>
  <li><strong>Choose unwaxed lemons</strong> - Organic or farmers market lemons are ideal since you'll eat the rind</li>
  <li><strong>Use enough salt</strong> - Don't skimp; salt is what prevents spoilage</li>
  <li><strong>Keep submerged</strong> - Any exposed lemons can develop mold</li>
  <li><strong>Rinse before using</strong> - As Cultured Guru notes, "Rinse off any excess salt and brine before using the preserved lemons in recipes"</li>
  <li><strong>Use primarily the rind</strong> - The pulp can be discarded or used in small amounts</li>
</ul>

<h2>Creative Uses for Preserved Lemons</h2>

<p>Once you have a jar of preserved lemons, the culinary possibilities expand:</p>

<ul>
  <li><strong>Moroccan Tagines:</strong> The classic use—add chopped preserved lemon to chicken or lamb tagines</li>
  <li><strong>Salad Dressings:</strong> Blend preserved lemon into vinaigrettes for complex citrus flavor</li>
  <li><strong>Roasted Vegetables:</strong> Toss with olive oil and chopped preserved lemon before roasting</li>
  <li><strong>Pasta:</strong> Add to pasta with olive oil, herbs, and olives</li>
  <li><strong>Hummus:</strong> Blend into hummus for a bright, salty twist</li>
  <li><strong>Grilled Fish:</strong> Use as a topping or in a compound butter</li>
</ul>

<h2>Storage and Shelf Life</h2>

<p>Properly made preserved lemons are remarkably shelf-stable. Taste of Maroc's expert notes, "Every year I make preserved lemons and for the first three or four months they are delicious." For longest life, always use a clean utensil to remove lemons from the jar and keep remaining lemons submerged in the brine.</p>

<h2>The Sustainable Choice</h2>

<p>Preserved lemons represent zero-waste cooking at its finest. When lemons are in season and abundant, preserving them means enjoying their flavor year-round without shipping fresh citrus across the globe. The <a href="https://citrusindustry.net/2025/10/23/citrus-concentrates-market-rise/" target="_blank" rel="noopener">Citrus Industry Magazine</a> reports the global citrus concentrates market is projected to rise from $9.69 billion in 2025 to $13.81 billion by 2032—a testament to our enduring love affair with citrus. Home preservation lets you enjoy that flavor sustainably.</p>

<h2>Start Your First Batch Today</h2>

<p>With <a href="https://silkroadrecipes.com/moroccan-preserved-lemons/" target="_blank" rel="noopener">Silk Road Recipes</a> noting "All you need is fruit, some salt, a few spices, and some patience to easily prepare a jar full of these succulent, citrusy treats in your own kitchen," there's no reason not to start today. In just a few weeks, you'll have a transformative ingredient that will make you wonder how you ever cooked without it.</p>
"""


def find_article():
    url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json"
    headers = {"X-Shopify-Access-Token": TOKEN}
    params = {"limit": 250}

    response = requests.get(url, headers=headers, params=params)
    articles = response.json().get("articles", [])

    for article in articles:
        if "Preserved Lemon" in article["title"]:
            return article
    return None


def update_article(article_id):
    url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

    payload = {"article": {"id": article_id, "body_html": BODY_HTML}}

    response = requests.put(url, headers=headers, json=payload)
    return response


if __name__ == "__main__":
    print("🍋 Republishing Topic 25: Preserved Lemons")
    print("=" * 50)

    article = find_article()
    if article:
        print(f"Found: {article['title']}")
        print(f"ID: {article['id']}")

        response = update_article(article["id"])
        if response.status_code == 200:
            print("✅ Article updated successfully!")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
    else:
        print("❌ Article not found!")
