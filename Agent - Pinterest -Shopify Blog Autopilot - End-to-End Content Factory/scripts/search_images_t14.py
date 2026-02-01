#!/usr/bin/env python3
"""Topic 14: Herbal Infusions vs Decoctions - Image Search"""

import requests
import json
import os

PEXELS_API_KEY = "os.environ.get("PEXELS_API_KEY", "")"

queries = [
    "herbal tea infusion teapot leaves",
    "simmering herbs pot decoction",
    "dried roots herbs natural medicine",
    "chamomile flowers tea brewing",
    "ginger turmeric roots cooking",
]


def search_pexels(query, per_page=5):
    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "per_page": per_page, "orientation": "landscape"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json().get("photos", [])
    return []


def main():
    all_images = []
    used_ids = set()

    for query in queries:
        photos = search_pexels(query)
        for photo in photos:
            if photo["id"] not in used_ids:
                all_images.append(
                    {
                        "id": photo["id"],
                        "url": photo["src"]["large"],
                        "alt": photo.get("alt", query),
                        "photographer": photo.get("photographer", "Pexels"),
                        "query": query,
                    }
                )
                used_ids.add(photo["id"])
                break

    output_path = os.path.join(
        os.path.dirname(__file__), "..", "content", "images.json"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_images, f, indent=2)

    print(
        f"✅ Found {len(all_images)} unique images for Topic 14: Herbal Infusions vs Decoctions"
    )
    for img in all_images:
        print(f"  - {img['query']}: {img['url'][:60]}...")


if __name__ == "__main__":
    main()
