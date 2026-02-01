#!/usr/bin/env python3
"""
Reconcile nhẹ: đọc anti_drift_run_log.csv (và nguồn khác nếu có),
tổng hợp pass/fail → ghi recommendation vào config/decision_log.json.
Chạy: python reconcile_decision.py [--last N] (từ pipeline_v2 hoặc repo root).
  --last N   Chỉ xét N dòng gần nhất (theo timestamp) để đề xuất theo trend gần đây.
  RECONCILE_LAST_N=N  Tương đương --last N.
"""
from pathlib import Path
import argparse
import csv
import json
import os
from datetime import datetime, timezone

# Paths: script nằm trong pipeline_v2
PIPELINE_DIR = Path(__file__).resolve().parent
ROOT_DIR = PIPELINE_DIR.parent
RUN_LOG = PIPELINE_DIR / "anti_drift_run_log.csv"
DECISION_LOG = ROOT_DIR / "config" / "decision_log.json"

# Ngưỡng: tỉ lệ fail > FAIL_RATE_THRESHOLD thì đề xuất pause_and_review
FAIL_RATE_THRESHOLD = 0.5
HISTORY_MAX = 10


def read_run_log(last_n: int | None = None) -> tuple[int, int, int]:
    """
    Đọc anti_drift_run_log.csv.
    Mỗi dòng là một lần chạy; cùng article_id có thể có nhiều dòng.
    Chỉ lấy kết quả mới nhất theo từng article_id (theo timestamp) rồi đếm pass/fail theo bài.
    Nếu last_n set: chỉ xét N dòng gần nhất (theo timestamp) rồi mới tính latest per article.
    """
    passed, failed = 0, 0
    if not RUN_LOG.exists():
        return passed, failed, 0
    rows: list[dict] = []
    try:
        with open(RUN_LOG, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"Warn: read_run_log {e}")
        return passed, failed, 0
    if not rows:
        return passed, failed, 0
    # Sắp xếp theo timestamp giảm (mới nhất trước), lấy last_n dòng nếu có
    ts_key = "timestamp"
    rows_sorted = sorted(rows, key=lambda r: (r.get(ts_key) or ""), reverse=True)
    if last_n is not None and last_n > 0:
        rows_sorted = rows_sorted[:last_n]
    # article_id -> (timestamp, row) để giữ dòng mới nhất theo bài (trong tập đã lọc)
    latest_by_article: dict[str, tuple[str, dict]] = {}
    for row in rows_sorted:
        ts = (row.get(ts_key) or "").strip()
        aid = (row.get("article_id") or "").strip() or (row.get("title") or "").strip() or f"_{len(latest_by_article)}"
        if aid not in latest_by_article or (ts and ts > latest_by_article[aid][0]):
            latest_by_article[aid] = (ts, row)
    for _ts, row in latest_by_article.values():
        status = (row.get("status") or "").strip().lower()
        gate_pass = (row.get("gate_pass") or "").strip().lower()
        if status in ("done", "passed") or gate_pass in ("true", "1"):
            passed += 1
        else:
            failed += 1
    total = passed + failed
    return passed, failed, total


def compute_recommendation(passed: int, failed: int, total: int) -> tuple[str, str]:
    """
    Đề xuất last_decision và reason.
    Returns (last_decision, reason).
    """
    if total == 0:
        return "no_data", "Chưa có dữ liệu từ anti_drift_run_log.csv"
    fail_rate = failed / total if total else 0
    if passed == 0:
        return (
            "review_only",
            f"Chưa có bài nào pass (theo kết quả mới nhất từng bài). Chạy review/draft bình thường; bật publish khi đã có bài pass.",
        )
    if fail_rate > FAIL_RATE_THRESHOLD:
        return (
            "pause_and_review",
            f"Tỉ lệ fail cao ({failed}/{total}, {fail_rate:.0%}). Nên tạm dừng publish và review.",
        )
    if failed > 0:
        return (
            "review_only",
            f"Có {failed} bài fail, {passed} pass. Chạy review/draft trước khi bật publish.",
        )
    return (
        "continue_publish",
        f"Tất cả {total} bài pass. Có thể tiếp tục publish nếu WF_ENABLED và ALLOW_PUBLISH đã bật.",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile: aggregate run log → decision_log.json")
    parser.add_argument("--last", type=int, default=None, metavar="N", help="Chỉ xét N dòng gần nhất (theo timestamp)")
    args = parser.parse_args()
    last_n = args.last
    if last_n is None:
        try:
            last_n = int(os.environ.get("RECONCILE_LAST_N", "") or "0")
            if last_n <= 0:
                last_n = None
        except ValueError:
            last_n = None
    if last_n:
        print(f"Using last {last_n} rows (trend gần đây)")
    passed, failed, total = read_run_log(last_n=last_n)
    decision, reason = compute_recommendation(passed, failed, total)
    at = datetime.now(timezone.utc).isoformat()
    metrics = {
        "review_pass": passed,
        "review_fail": failed,
        "auto_fix_done": passed,  # từ run_log coi như auto-fix/review
        "publish_success": 0,  # có thể bổ sung từ nguồn khác sau
        "publish_fail": 0,
    }

    DECISION_LOG.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if DECISION_LOG.exists():
        try:
            with open(DECISION_LOG, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    if not data:
        data = {"history": []}

    # Giữ lại history cũ, thêm entry hiện tại vào đầu history (trước khi ghi đè last_*)
    prev = {
        "decision": data.get("last_decision"),
        "reason": data.get("reason"),
        "at": data.get("at"),
        "metrics": data.get("metrics"),
    }
    history = list(data.get("history") or [])
    if prev.get("at"):
        history.insert(0, prev)
    history = history[:HISTORY_MAX]

    data["last_decision"] = decision
    data["reason"] = reason
    data["at"] = at
    data["source"] = "reconcile_script"
    data["metrics"] = metrics
    data["history"] = history

    with open(DECISION_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Reconcile: {decision}")
    print(f"Reason: {reason}")
    print(f"Metrics: pass={passed} fail={failed} total={total}")
    print(f"Written: {DECISION_LOG}")


if __name__ == "__main__":
    main()
