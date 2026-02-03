#!/usr/bin/env python3
"""
Restore Shopify articles from local backups.

Default behavior:
- Scan backups_auto_fix/*.json
- For each article: run pre_publish_review on current article
- If current FAILS, restore from backup, then re-run review
- Save current version to backups_restore/ before overwriting
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import requests
import subprocess
from dotenv import load_dotenv

PIPELINE_DIR = Path(__file__).parent
CONTENT_DIR = PIPELINE_DIR.parent
BACKUP_DIR = PIPELINE_DIR / "backups_auto_fix"
RESTORE_DIR = PIPELINE_DIR / "backups_restore"
REVIEW_SCRIPT = CONTENT_DIR / "scripts" / "pre_publish_review.py"

# Load env from common locations
for env_path in [
    CONTENT_DIR / ".env",
    PIPELINE_DIR / ".env",
    CONTENT_DIR.parent / ".env",
]:
    if env_path.exists():
        load_dotenv(env_path)

SHOP = os.environ.get("SHOPIFY_STORE_DOMAIN") or os.environ.get("SHOPIFY_SHOP", "")
TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN") or os.environ.get("SHOPIFY_TOKEN")
BLOG_ID = os.environ.get("SHOPIFY_BLOG_ID", "")
API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2025-01")

if not SHOP or not TOKEN or not BLOG_ID:
    raise SystemExit("Missing Shopify config. Set SHOPIFY_STORE_DOMAIN/SHOPIFY_SHOP, SHOPIFY_ACCESS_TOKEN, SHOPIFY_BLOG_ID.")

HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}


def _extract_id_from_name(name: str) -> str | None:
    match = re.match(r"(\d+)_backup\.json$", name)
    return match.group(1) if match else None


def _get_article(article_id: str) -> dict | None:
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        print(f"[WARN] Fetch article {article_id} failed: HTTP {resp.status_code}")
        return None
    return resp.json().get("article")


def _save_current_backup(article: dict, article_id: str) -> Path:
    RESTORE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RESTORE_DIR / f"{article_id}_current_{ts}.json"
    path.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _restore_from_backup(backup: dict, article_id: str) -> bool:
    url = f"https://{SHOP}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles/{article_id}.json"
    payload = {
        "article": {
            "id": int(article_id),
            "title": backup.get("title", ""),
            "body_html": backup.get("body_html", ""),
            "summary_html": backup.get("summary_html", ""),
            "tags": backup.get("tags", ""),
            "author": backup.get("author", ""),
            "handle": backup.get("handle", ""),
            "image": backup.get("image", None),
            "published_at": backup.get("published_at", None),
        }
    }
    resp = requests.put(url, headers=HEADERS, data=json.dumps(payload), timeout=60)
    if resp.status_code not in {200, 201}:
        print(f"[FAIL] Restore {article_id} failed: HTTP {resp.status_code} {resp.text[:200]}")
        return False
    print(f"[OK] Restored article {article_id} from backup.")
    return True


def _run_review(article_id: str) -> bool:
    if not REVIEW_SCRIPT.exists():
        print("[WARN] pre_publish_review.py not found; skipping review.")
        return True
    try:
        result = subprocess.run(
            [sys.executable, str(REVIEW_SCRIPT), str(article_id)],
            cwd=str(CONTENT_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0 and result.stderr:
            print(f"[WARN] pre_publish_review: {result.stderr[:200]}")
        return result.returncode == 0
    except Exception as exc:
        print(f"[WARN] pre_publish_review failed to run: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", help="Comma-separated article IDs")
    parser.add_argument("--from-file", help="File with article IDs (one per line)")
    parser.add_argument("--limit", type=int, default=5, help="Max items to restore")
    parser.add_argument("--force", action="store_true", help="Restore even if current passes review")
    parser.add_argument(
        "--keep-failed",
        action="store_true",
        help="Keep backup even if it fails review (default reverts to current)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Shopify")
    args = parser.parse_args()

    ids: list[str] = []
    if args.ids:
        ids.extend([x.strip() for x in args.ids.split(",") if x.strip()])
    if args.from_file:
        path = Path(args.from_file)
        if path.exists():
            ids.extend([x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()])

    if not ids:
        backup_files = sorted(BACKUP_DIR.glob("*_backup.json"))
        for backup in backup_files:
            aid = _extract_id_from_name(backup.name)
            if aid:
                ids.append(aid)

    restored = 0
    skipped = 0
    reviewed = 0
    log_entries = []
    for article_id in ids:
        if restored >= args.limit:
            break
        backup_path = BACKUP_DIR / f"{article_id}_backup.json"
        if not backup_path.exists():
            continue

        print(f"\n[CHECK] Article {article_id}")
        current = _get_article(article_id)
        if not current:
            continue

        if not args.force:
            reviewed += 1
            current_pass = _run_review(article_id)
            if current_pass:
                print("[SKIP] Current article passes review.")
                skipped += 1
                log_entries.append({"id": article_id, "action": "skip", "reason": "current_pass"})
                continue

        if args.dry_run:
            print("[DRY] Would restore from backup.")
            restored += 1
            log_entries.append({"id": article_id, "action": "dry_run_restore"})
            continue

        current_backup = _save_current_backup(current, article_id)
        backup = json.loads(backup_path.read_text(encoding="utf-8"))
        if _restore_from_backup(backup, article_id):
            backup_pass = _run_review(article_id)
            if backup_pass or args.keep_failed:
                restored += 1
                log_entries.append({"id": article_id, "action": "restored"})
            else:
                # Revert to current if backup still fails review
                revert_payload = json.loads(current_backup.read_text(encoding="utf-8"))
                _restore_from_backup(revert_payload, article_id)
                print(f"[REVERT] Backup failed review; restored current version for {article_id}")
                log_entries.append({"id": article_id, "action": "revert", "reason": "backup_failed_review"})
        time.sleep(2)

    summary = {
        "restored": restored,
        "skipped": skipped,
        "reviewed": reviewed,
        "total_considered": len(ids),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entries": log_entries,
    }
    log_path = PIPELINE_DIR / "restore_from_backups_log.json"
    log_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nDone. Restored: {restored}, Skipped: {skipped}, Reviewed: {reviewed}")
    print(f"[LOG] {log_path}")


if __name__ == "__main__":
    main()
