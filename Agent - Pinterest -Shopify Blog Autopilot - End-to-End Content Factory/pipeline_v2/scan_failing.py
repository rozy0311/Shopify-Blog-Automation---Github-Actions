#!/usr/bin/env python3
"""Quick scan to find articles failing quality gate."""
import sys

sys.path.insert(0, ".")
from ai_orchestrator import ShopifyAPI, QualityGate

print("Scanning all published articles...")
articles = ShopifyAPI.get_all_articles(status="any", limit=250)
print(f"Found {len(articles)} articles")

failing = []
passing = []
for art in articles:
    result = QualityGate.full_audit(art)
    score = result.get("score", 0)
    if not result.get("pass") or score < 9:
        failing.append(
            {
                "id": art.get("id"),
                "title": art.get("title", "")[:50],
                "score": score,
                "issues": result.get("issues", [])[:2],
            }
        )
    else:
        passing.append(art.get("id"))

print(f"\n✅ Passing: {len(passing)} articles")
print(f"❌ Failing: {len(failing)} articles")

print(f"\nFailing articles (first 30):")
for f in failing[:30]:
    print(f"  {f['id']}: score={f['score']} - {f['issues'][:2]}")

# Save failing IDs to file
with open("failing_articles.txt", "w") as fp:
    for f in failing:
        fp.write(f"{f['id']}\n")
print(f"\nSaved {len(failing)} failing IDs to failing_articles.txt")
