#!/usr/bin/env python3
"""Scan all articles and find ones failing the quality gate."""
import sys
import json

sys.path.insert(0, ".")
from ai_orchestrator import ShopifyAPI, QualityGate

print("Scanning articles for gate failures...")
articles = ShopifyAPI.get_all_articles(status="any", limit=250)
print(f"Total articles: {len(articles)}")

failed = []
for i, a in enumerate(articles):
    result = QualityGate.full_audit(a)
    score = result.get("score", 0)
    if score < 9:
        failed.append(
            {
                "id": a.get("id"),
                "title": a.get("title", "")[:50],
                "score": score,
                "issues": result.get("issues", [])[:2],
            }
        )
    if (i + 1) % 50 == 0:
        print(f"  Scanned {i+1}/{len(articles)}...")

print(f"\nArticles failing gate (score < 9): {len(failed)}")
for f in failed[:15]:
    print(f"  {f['id']}: score={f['score']} - {f['title']}")
if len(failed) > 15:
    print(f"  ... and {len(failed)-15} more")

# Save to file
with open("articles_to_rebuild.json", "w") as fp:
    json.dump([x["id"] for x in failed], fp)
print(f"\nSaved {len(failed)} article IDs to articles_to_rebuild.json")
