import requests
import json

config = json.loads(open("SHOPIFY_PUBLISH_CONFIG.json").read())
shop = config["shop"]
url = f"https://{shop['domain']}/admin/api/{shop['api_version']}/graphql.json"
headers = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": shop["access_token"],
}

query = """
query {
  article(id: "gid://shopify/Article/690495095102") {
    id
    title
    body
    image {
      url
    }
  }
}
"""

resp = requests.post(url, headers=headers, json={"query": query})
data = resp.json()
article = data.get("data", {}).get("article", {})
print("Title:", article.get("title"))
print("Has featured image:", article.get("image"))
body = article.get("body", "")
print("Body has <img>:", "<img" in body)
print("Body has <figure>:", "<figure" in body)
print("Body length:", len(body))

# Count images
import re

img_count = len(re.findall(r"<img", body))
figure_count = len(re.findall(r"<figure", body))
print(f"Image tags found: {img_count}")
print(f"Figure tags found: {figure_count}")

# Show image URLs if any
img_urls = re.findall(r'src="([^"]+)"', body)
print(f"\nImage URLs in body:")
for i, url in enumerate(img_urls[:5]):
    print(f"  {i+1}. {url[:80]}...")
