# Decision Log (Reconcile layer)

File **`decision_log.json`** lưu quyết định gần nhất và số liệu tổng hợp từ pipeline (review / auto-fix / publish). Supervisor hoặc script reconcile đọc/ghi file này.

## Schema

| Field | Ý nghĩa |
|-------|---------|
| `last_decision` | `continue_publish` \| `pause_and_review` \| `review_only` \| `no_data` |
| `reason` | Lý do ngắn (string) |
| `at` | ISO timestamp lần cập nhật cuối |
| `source` | `reconcile_script` \| `supervisor` \| `manual` |
| `metrics` | Số liệu: review_pass, review_fail, auto_fix_done, publish_success, publish_fail |
| `history` | Mảng các entry cũ (optional), mỗi entry: { decision, reason, at, metrics } |

## Ai ghi vào đây

- **Script** `pipeline_v2/reconcile_decision.py`: đọc `anti_drift_run_log.csv` (và nguồn khác nếu có), tổng hợp → ghi `last_decision`, `reason`, `at`, `metrics`.
- **Supervisor** (repo GitHub Actions): sau khi dispatch review/publish hoặc disable pipeline, có thể ghi `last_decision` + `reason` vào file này (nếu repo có quyền ghi vào đây).
- **Human**: sửa trực tiếp khi cần (vd. force `pause_and_review`).

## Giá trị last_decision

- **`continue_publish`**: Pipeline ổn, có thể tiếp tục publish.
- **`pause_and_review`**: Nên tạm dừng publish, human review (nhiều fail, hoặc incident).
- **`review_only`**: Chỉ chạy review/draft, chưa bật publish.
- **`no_data`**: Chưa đủ dữ liệu để đề xuất (lần chạy reconcile đầu hoặc thiếu log).

## Ghi chú nguồn dữ liệu

- **anti_drift_run_log.csv** có thể chỉ ghi các lần chạy **failed** (mỗi dòng một lần fix/review). Khi đó `review_pass` = 0 là bình thường; recommendation sẽ là `review_only` hoặc `pause_and_review` cho đến khi có nguồn khác (vd. publish success) hoặc log bắt đầu ghi cả pass. Script hỗ trợ `--last N` hoặc env `RECONCILE_LAST_N=N` để chỉ xét N dòng gần nhất (theo timestamp) → đề xuất theo trend gần đây.
