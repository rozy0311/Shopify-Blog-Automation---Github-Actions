#!/usr/bin/env python3
"""Quick fix for specific article in queue"""
import json
from pathlib import Path

queue_path = Path(__file__).parent / 'anti_drift_queue.json'
data = json.loads(queue_path.read_text(encoding='utf-8'))

# Articles to mark as done (validated manually)
validated_ids = [682731602238]

for item in data.get('items', []):
    if item.get('id') in validated_ids:
        item['status'] = 'done'
        item['notes'] = 'Validated manually - passes quality checks'
        print(f"Marked {item['id']} as done")

queue_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
print('Queue updated')
