import requests
import json

PEXELS_API_KEY = "os.environ.get("PEXELS_API_KEY", "")"
headers = {"Authorization": PEXELS_API_KEY}

queries = [
    "granola oats",
    "homemade granola bowl",
    "yogurt granola berries",
    "healthy breakfast cereal",
    "nuts seeds oats",
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

selected = all_images[:5]
print(f"Found {len(selected)} images")

with open("../content/images.json", "w") as f:
    json.dump(selected, f, indent=2)
print("Saved to images.json")
