#!/usr/bin/env python3
"""Search Pexels images for Topic 21: Natural Fabric Dyes"""

import requests
import json

PEXELS_API_KEY = "os.environ.get("PEXELS_API_KEY", "")"
headers = {"Authorization": PEXELS_API_KEY}

queries = [
    "natural fabric dye",
    "vegetable dye fabric",
    "tie dye fabric colorful",
    "hand dyeing fabric",
    "eco friendly textile",
]
all_images = []
seen_ids = set()

for query in queries:
    url = f"https://api.pexels.com/v1/search?query={query}&per_page=3"
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 200:
        for photo in response.json().get("photos", []):
            if photo["id"] not in seen_ids:
                seen_ids.add(photo["id"])
                all_images.append(
                    {
                        "id": photo["id"],
                        "url": photo["src"]["large"],
                        "alt": photo.get("alt", "Natural fabric dyeing"),
                        "photographer": photo["photographer"],
                    }
                )

print(f"Found {len(all_images)} images")
print()
for i, img in enumerate(all_images[:6]):
    alt_text = img["alt"][:60] if img["alt"] else "Natural dyeing"
    print(f"{i+1}. {alt_text}")
    print(f"   Photographer: {img['photographer']}")
    print(f"   URL: {img['url']}")
    print()

# Save to JSON for later use
with open("topic21_images.json", "w") as f:
    json.dump(all_images[:6], f, indent=2)
print("Saved to topic21_images.json")
