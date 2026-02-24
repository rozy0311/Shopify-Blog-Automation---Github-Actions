import json

d = json.load(open("artifact-downloads/force-rescan/anti_drift_queue.json"))
items = d["items"]

# Count by status
status_counts = {}
for i in items:
    s = i.get("status", "unknown")
    status_counts[s] = status_counts.get(s, 0) + 1

print("=== Queue Summary ===")
print(f"Total: {len(items)}")
for k, v in sorted(status_counts.items()):
    print(f"  {k}: {v}")
print(f'\nRun Counter: {d.get("run_counter")}')
print(f'Last Updated: {d.get("updated_at")}')

# Show pending articles
pending = [i for i in items if i.get("status") in ("pending", "failed", "retrying")]
print(f"\n=== Pending/Failed/Retrying ({len(pending)}) ===")
for p in pending[:10]:
    print(
        f'  - [{p["id"]}] {p.get("title", "")[:50]}... | attempts: {p.get("attempts")} | error: {p.get("last_error", "")[:30]}'
    )
if len(pending) > 10:
    print(f"  ... and {len(pending) - 10} more")

# Show manual review
manual = [i for i in items if i.get("status") == "manual_review"]
print(f"\n=== Manual Review ({len(manual)}) ===")
for m in manual[:5]:
    print(
        f'  - [{m["id"]}] {m.get("title", "")[:50]}... | error: {m.get("last_error", "")[:50]}'
    )
if len(manual) > 5:
    print(f"  ... and {len(manual) - 5} more")
