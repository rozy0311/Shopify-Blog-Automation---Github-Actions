#!/usr/bin/env python3
"""Temp script to check queue status"""
import json
from pathlib import Path
from collections import Counter

queue = json.loads(Path("anti_drift_queue.json").read_text(encoding="utf-8"))
items = queue.get("items", [])

statuses = Counter(item.get("status") for item in items)
print("=== QUEUE STATUS ===")
for status, count in statuses.most_common():
    print(f"{status}: {count}")

# Show pending items
pending = [i for i in items if i.get("status") == "pending"]
print(f"\n=== TOP 10 PENDING ===")
for item in pending[:10]:
    issues = item.get("issues", [])[:2]
    print(f"ID: {item.get('id')} | Issues: {issues}")

# Check specific article 682731602238
print("\n=== ARTICLE 682731602238 ===")
target = [i for i in items if str(i.get("id")) == "682731602238"]
if target:
    print(json.dumps(target[0], indent=2, ensure_ascii=False))
else:
    print("Not found in queue")
