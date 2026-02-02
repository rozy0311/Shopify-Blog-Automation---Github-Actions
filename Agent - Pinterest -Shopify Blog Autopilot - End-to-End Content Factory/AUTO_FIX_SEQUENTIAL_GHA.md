# Auto Fix Sequential - GitHub Actions

## Tại sao không thấy publish / không chạy mỗi 10 phút / không thấy kết quả?

### 1. **Schedule mỗi 10 phút**

- GitHub Actions **chỉ chạy schedule trên default branch** của repo.
- Nếu default branch là `main` mà code/workflow mới nằm trên `feat/l6-reconcile-main` → schedule sẽ chạy bản trên `main` (có thể cũ hoặc thiếu file).
- **Cách xử lý:** Vào repo **Settings → General → Default branch** → đổi thành **feat/l6-reconcile-main** (hoặc merge code vào `main` rồi dùng `main` làm default).

### 2. **Queue không tìm thấy → không có bài để fix/publish**

- Trước đây queue được ghi ở **repo root** (`anti_drift_queue.json`) trong khi workflow chạy trong thư mục **pipeline_v2** → không tìm thấy file → "No queue found; skipping fix loop".
- **Đã sửa:** Queue và log giờ nằm trong **pipeline_v2** (`anti_drift_queue.json`, `anti_drift_run_log.csv`) nên GHA tìm được và có thể xử lý + publish khi review pass.

### 3. **Xem kết quả**

- Mỗi run có bước **"Job summary"** in ra: số item trong queue, pending, done.
- Artifact **auto-fix-sequential**: tải về để xem `anti_drift_queue.json`, `review-output-*.txt`.
- Log từng bước: **Actions → chọn run → job "auto-fix-one"** → xem từng step (Scan issues, Fix, Review, Publish).

### 4. **Flow đạt chuẩn META-PROMPT (Review → Cleanup → Publish)**

- **queue-run** (1 bài): meta fix → gate 9/10 → nếu **gate pass**:
  1. Chạy **pre_publish_review** (scripts/pre_publish_review.py) cho bài đó.
  2. Nếu **review pass**: chạy **cleanup_before_publish** (strip generic sections, dedupe, featured image) rồi **publish_now_graphql** → mark_done.
  3. Nếu review fail: thử auto_fix_article; vẫn fail thì mark_retry / mark_failed.
- Chuẩn review: 11-section structure (gợi ý), 5+ sources (format Name — Description), 2+ expert quotes, 3+ stats, no generic phrases, no raw URL trong link text.
- Cần **Secrets** đúng: `SHOPIFY_SHOP`, `SHOPIFY_ACCESS_TOKEN`, `SHOPIFY_BLOG_ID` (đúng store/blog bạn đang xem).
