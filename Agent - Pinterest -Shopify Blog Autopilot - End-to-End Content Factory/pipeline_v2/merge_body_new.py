#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE_PATH = (
    ROOT
    / "Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory"
    / "pipeline_v2"
    / "fix_queue_15.json"
)


def normalize_rel(path_str: str) -> Path:
    return ROOT / path_str


def main():
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    updated = 0
    skipped = 0

    for item in queue:
        body_new_path = item.get("body_new_path")
        file_path = item.get("file_path")
        if not body_new_path or not file_path:
            skipped += 1
            continue

        json_path = normalize_rel(file_path)
        html_path = normalize_rel(body_new_path)
        if not json_path.exists() or not html_path.exists():
            skipped += 1
            continue

        data = json.loads(json_path.read_text(encoding="utf-8"))
        new_body = html_path.read_text(encoding="utf-8").strip()
        data["body_html"] = new_body
        json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        updated += 1

    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
