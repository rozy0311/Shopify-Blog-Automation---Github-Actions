# Fix blog đã publish (generic content / ảnh lỗi ngón tay)

## Cách lấy danh sách bài cần fix

1. **Re-audit trên GHA** (báo cáo chất lượng):
   - Vào repo → Actions → "re-audit-dispatch" → Run workflow (limit 250).
   - Sau khi chạy xong, tải artifact "quality-report" (quality_report_*.json, meta_prompt_quality_report_*.json).
   - Mở JSON, tìm các bản ghi `"passed": false` → lấy `article_id` (hoặc `id`).

2. **Từ conversation / log**: dùng các ID đã biết (vd: 691791954238, 691731595582).

## Trigger fix từng bài (Article Pre-Publish Review)

```bash
# Một bài
gh workflow run "Article Pre-Publish Review" --ref feat/l6-reconcile-main -f article_id=691791954238

# Xem run vừa tạo
gh run list --workflow="Article Pre-Publish Review" -L 1

# Xem log (thay RUN_ID)
gh run view RUN_ID --log-failed
gh run watch RUN_ID
```

Workflow sẽ: review → nếu fail thì fix-ids → review lại → force-rebuild + fix images → review lần 3 → nếu pass (hoặc publish_anyway): cleanup + set featured + publish.

## Trigger fix theo queue (Auto Fix Manual)

- Chạy queue (nhiều bài): Actions → "Auto Fix Manual Trigger" → Run, để trống article_id, fix_max_items=3.
- Một bài theo ID: nhập article_id, Run.

## Nếu review vẫn fail

- Bật **publish_anyway** khi trigger Article Pre-Publish Review để vẫn cleanup + set featured + publish (fix tối thiểu).
- Hoặc chỉnh script: thêm cụm generic vào `scripts/pre_publish_review.py` / `pipeline_v2/ai_orchestrator.py`, hoặc nới gate (tạm thời) rồi chạy lại.
