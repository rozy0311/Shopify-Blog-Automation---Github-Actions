#!/usr/bin/env python3
"""
Topic 26: Homemade Fruit Leather - Republish with hidden links and researched content
Sources:
- Simply Recipes - How to Make Fruit Leather
- Wholesome Yum - Easy Fruit Leather Recipe
- Market.us - Dried Fruit Snacks $19.4 billion
- Future Market Insights - US Fruit Snacks Market
"""

import requests

SHOP = "the-rike-inc.myshopify.com"
TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
BLOG_ID = "108441862462"

ARTICLE_TITLE = "Homemade Fruit Leather: A Healthy Snack with Zero Added Sugar"

BODY_HTML = """
<p>Remember those brightly colored fruit roll-ups from childhood? The homemade version is infinitely better—and healthier. With the <a href="https://media.market.us/healthy-snack-statistics/" target="_blank" rel="noopener">healthy snack market</a> reporting dried fruit snacks valued at $19.4 billion, there's clearly a massive appetite for fruit-based treats. The good news? You can make superior fruit leather at home with nothing but real fruit and perhaps a touch of honey.</p>

<h2>Why Make Your Own Fruit Leather?</h2>

<p>Commercial fruit snacks often contain added sugars, artificial colors, and preservatives. As <a href="https://www.wholesomeyum.com/fruit-leather/" target="_blank" rel="noopener">Wholesome Yum</a> explains, "This healthy fruit leather recipe is my homemade version of fruit rollups. It's so easy to make with real, fresh fruit and no added sugar!"</p>

<p>According to <a href="https://www.futuremarketinsights.com/reports/united-states-fruit-snacks-market" target="_blank" rel="noopener">Future Market Insights</a>, "Organic is the leading product claim in the fruit snack market in the USA, capturing 34.2% of the demand." Making your own means you control exactly what goes in—and what stays out.</p>

<h2>The Basic Method: No Special Equipment Required</h2>

<p><a href="https://www.simplyrecipes.com/recipes/how_to_make_fruit_leather/" target="_blank" rel="noopener">Simply Recipes</a> notes that "the nice thing about fruit leather is that you don't need to add sugar or lemon to preserve the fruit." Here's how simple the process really is:</p>

<h3>What You'll Need:</h3>
<ul>
  <li>2-3 cups fresh or frozen fruit (berries, peaches, mangoes, apples)</li>
  <li>1-2 tablespoons honey or maple syrup (optional)</li>
  <li>1 tablespoon lemon juice (helps preserve color)</li>
  <li>Baking sheet lined with parchment paper or silicone mat</li>
</ul>

<h3>Oven Method (No Dehydrator Needed):</h3>

<ol>
  <li><strong>Blend the fruit:</strong> Purée your fruit until completely smooth. Add honey if the fruit is tart.</li>
  <li><strong>Spread evenly:</strong> Pour onto a parchment-lined baking sheet, spreading to about 1/8-inch thickness. Make edges slightly thicker as they dry faster.</li>
  <li><strong>Dry low and slow:</strong> Bake at your oven's lowest setting (170-200°F). As recommended by experienced dehydrators, "Bake for 8-12 hours at 140°F, 5-8 hours at 150°F, or 3-5 hours at 170°F, checking periodically."</li>
  <li><strong>Test for doneness:</strong> The leather is ready when it's no longer sticky to the touch and peels away cleanly from the parchment.</li>
</ol>

<h2>Dehydrator Method</h2>

<p>If you have a dehydrator, the process is even easier. According to Simply Recipes, "8 to 10 hours is the sweet range for making fruit leather in our dehydrator." Set your dehydrator to 135-145°F and spread the purée on the fruit leather trays.</p>

<h2>Winning Flavor Combinations</h2>

<p>The beauty of homemade fruit leather is experimenting with flavors. Try these crowd-pleasing combinations:</p>

<ul>
  <li><strong>Classic Strawberry:</strong> As <a href="https://weelicious.com/strawberr-wee-fruit-leather-program/" target="_blank" rel="noopener">Weelicious</a> describes, "This homemade strawberry fruit leather is easy to make in the oven with just strawberries and a touch of honey."</li>
  <li><strong>Tropical Mango:</strong> Mango with a squeeze of lime juice</li>
  <li><strong>Apple Cinnamon:</strong> Applesauce with cinnamon (the easiest starting point)</li>
  <li><strong>Berry Blend:</strong> Mixed berries for antioxidant power</li>
  <li><strong>Peach Ginger:</strong> Ripe peaches with fresh grated ginger</li>
  <li><strong>Watermelon Mint:</strong> Refreshing summer favorite</li>
</ul>

<h2>Tips for Perfect Fruit Leather Every Time</h2>

<ul>
  <li><strong>Use ripe fruit:</strong> The riper the fruit, the sweeter your leather—no added sugar needed</li>
  <li><strong>Strain if needed:</strong> For berries with seeds (like raspberries), strain the purée first</li>
  <li><strong>Keep it thin:</strong> Too thick and it won't dry properly; too thin and edges will crack</li>
  <li><strong>Watch the edges:</strong> Make edges slightly thicker since they dry first</li>
  <li><strong>Prop oven door:</strong> Leave it slightly ajar for moisture to escape</li>
  <li><strong>Test often:</strong> Check every hour after the 6-hour mark</li>
</ul>

<h2>Storage and Shelf Life</h2>

<p>When the leather peels easily from the parchment, it's done. Simply Recipes confirms that "when the fruit leather is ready, you can easily peel it up from the plastic wrap." To store:</p>

<ol>
  <li>Let cool completely on the pan</li>
  <li>Roll up in parchment paper or plastic wrap</li>
  <li>Cut into strips with scissors if desired</li>
  <li>Store in an airtight container at room temperature for 2-3 weeks</li>
  <li>Refrigerate for 2-3 months, or freeze for up to a year</li>
</ol>

<h2>Using Seasonal and Imperfect Fruit</h2>

<p>Fruit leather is the perfect solution for:</p>
<ul>
  <li>Overripe bananas and bruised peaches</li>
  <li>Farmers market fruit that's past its prime</li>
  <li>End-of-season berry abundance</li>
  <li>Frozen fruit you need to use up</li>
</ul>

<p>This is zero-waste cooking at its best—transforming fruit that might otherwise be discarded into a shelf-stable snack that kids and adults alike devour.</p>

<h2>A Healthier Snack Revolution</h2>

<p>Research shows the fruit snacks market is growing "due to a shift in consumer demand towards healthier snacking options" and "higher demand for chemical-free, fat-free, and lower-calorie options." By making fruit leather at home, you're joining a movement toward real-food snacking that tastes better and costs less than store-bought alternatives.</p>

<p>Start with a simple batch of applesauce leather (just spread unsweetened applesauce and dry), and once you've mastered the technique, experiment with seasonal fruits and creative combinations. Your pantry—and your family—will thank you.</p>
"""


def find_article():
    url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles.json"
    headers = {"X-Shopify-Access-Token": TOKEN}
    params = {"limit": 250}

    response = requests.get(url, headers=headers, params=params)
    articles = response.json().get("articles", [])

    for article in articles:
        if "Fruit Leather" in article["title"]:
            return article
    return None


def update_article(article_id):
    url = f"https://{SHOP}/admin/api/2025-01/blogs/{BLOG_ID}/articles/{article_id}.json"
    headers = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

    payload = {"article": {"id": article_id, "body_html": BODY_HTML}}

    response = requests.put(url, headers=headers, json=payload)
    return response


if __name__ == "__main__":
    print("🍓 Republishing Topic 26: Homemade Fruit Leather")
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
