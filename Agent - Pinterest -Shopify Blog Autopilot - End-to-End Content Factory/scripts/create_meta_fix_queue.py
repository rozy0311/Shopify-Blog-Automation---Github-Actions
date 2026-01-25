#!/usr/bin/env python3
"""
Create a sequential fix queue from meta_prompt_quality_report_*.json.

- Selects failed articles in report order (default all)
- Writes content/meta_fix_queue.json and content/meta_fix_queue.csv
"""

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
REPORT_DIR = ROOT_DIR.parent
CONTENT_DIR = ROOT_DIR / "content"


def pick_latest_report() -> Path:
    candidates = sorted(
        REPORT_DIR.glob("meta_prompt_quality_report_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise SystemExit("No meta_prompt_quality_report_*.json found in repo root")
    return candidates[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=str, default="")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    report_path = Path(args.report).resolve() if args.report else pick_latest_report()
    if not report_path.exists():
        raise SystemExit(f"Report not found: {report_path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    items = []

    for article in report.get("articles", []):
        if article.get("passed") is True:
            continue
        issues = article.get("issues", [])
        missing = [
            {
                "severity": i.get("severity"),
                "category": i.get("category"),
                "message": i.get("message"),
            }
            for i in issues
            if i.get("severity") in {"CRITICAL", "MAJOR", "MINOR"}
        ]
        items.append(
            {
                "article_id": str(article.get("id")),
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "score": article.get("score"),
                "status": "pending",
                "attempts": 0,
                "last_error": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "missing": missing,
            }
        )

    if args.limit and args.limit > 0:
        items = items[: args.limit]

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    queue_path = CONTENT_DIR / "meta_fix_queue.json"
    csv_path = CONTENT_DIR / "meta_fix_queue.csv"

    queue_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["article_id", "title", "score", "status", "missing"])
        for item in items:
            missing_text = "; ".join(
                f"{m.get('category')}: {m.get('message')}" for m in item["missing"]
            )
            writer.writerow(
                [
                    item["article_id"],
                    item["title"],
                    item["score"],
                    item["status"],
                    missing_text,
                ]
            )

    print(f"Created meta fix queue with {len(items)} items")
    print(f"- {queue_path}")
    print(f"- {csv_path}")


if __name__ == "__main__":
    main()
