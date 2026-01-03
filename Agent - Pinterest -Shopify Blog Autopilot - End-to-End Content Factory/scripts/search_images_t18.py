import requests
import json

API_KEY = "os.environ.get("PEXELS_API_KEY", "")"
HEADERS = {"Authorization": API_KEY}

queries = [
    "vegetable broth soup pot",
    "kitchen scraps vegetables cutting board",
    "homemade stock cooking pot",
    "celery carrots onions chopped",
    "vegetable peels food waste",
]

all_images = []
seen_ids = set()

for q in queries:
    url = f"https://api.pexels.com/v1/search?query={q}&per_page=5"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        for p in r.json().get("photos", []):
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                all_images.append(
                    {
                        "id": p["id"],
                        "url": p["src"]["large"],
                        "alt": p.get("alt", ""),
                        "photographer": p["photographer"],
                    }
                )

images = all_images[:5]
print(f"✅ Found {len(images)} unique images for Topic 18: Zero-Waste Vegetable Broth")

with open("../content/images.json", "w", encoding="utf-8") as f:
    json.dump(images, f, indent=2, ensure_ascii=False)
