import requests
import json
import os

PEXELS_API_KEY = "os.environ.get("PEXELS_API_KEY", "")"
queries = [
    "fresh ginger root",
    "ginger paste cooking",
    "asian stir fry wok",
    "meal prep containers",
    "curry spices ingredients",
]

headers = {"Authorization": PEXELS_API_KEY}
images = []
used_ids = set()

for q in queries:
    resp = requests.get(
        f"https://api.pexels.com/v1/search?query={q}&per_page=10", headers=headers
    )
    if resp.status_code == 200:
        for photo in resp.json().get("photos", []):
            if photo["id"] not in used_ids:
                images.append(
                    {
                        "id": photo["id"],
                        "url": photo["src"]["large"],
                        "alt": photo["alt"] or q,
                        "photographer": photo["photographer"],
                    }
                )
                used_ids.add(photo["id"])
                break
    if len(images) >= 5:
        break

print(f"Found {len(images)} images")
out_path = os.path.join(os.path.dirname(__file__), "..", "content", "images.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(images, f, indent=2)
print("Saved to images.json")
