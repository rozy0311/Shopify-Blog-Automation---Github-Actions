import requests
import json

PEXELS_API_KEY = "os.environ.get("PEXELS_API_KEY", "")"
headers = {"Authorization": PEXELS_API_KEY}

queries = [
    "vanilla beans",
    "vanilla extract bottle",
    "baking ingredients pantry",
    "glass jar kitchen",
    "homemade cooking",
]
all_images = []
used_ids = set()

for q in queries:
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers=headers,
        params={"query": q, "per_page": 5},
    )
    if r.ok:
        for photo in r.json().get("photos", []):
            img_id = photo["id"]
            if img_id not in used_ids:
                used_ids.add(img_id)
                all_images.append(
                    {
                        "id": img_id,
                        "url": photo["src"]["large"],
                        "alt": photo.get("alt", q),
                        "photographer": photo.get("photographer", "Pexels"),
                    }
                )

# Get 5 unique images
selected = all_images[:5]
print("Found images:")
for i, img in enumerate(selected):
    alt_text = img["alt"][:60] if img["alt"] else queries[i]
    print(f"{i+1}. ID:{img['id']}")
    print(f"   Alt: {alt_text}")
    print(f"   URL: {img['url']}")
    print()

# Save to file
with open("../content/images.json", "w") as f:
    json.dump(selected, f, indent=2)
print("Saved to content/images.json")
