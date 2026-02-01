# Fix 1 bài còn generic rồi publish

Dùng khi bài đã được workflow/queue xử lý nhưng **chưa publish** hoặc **vẫn còn generic** (ví dụ 691791954238).

## Cách 1: strip-and-publish (khuyến nghị)

Từ thư mục repo (có `.env` với `SHOPIFY_*`):

```bash
cd "Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory/pipeline_v2"
python ai_orchestrator.py strip-and-publish 691791954238
```

- Strip toàn bộ generic phrases khỏi `body_html` (cùng list với pre_publish_review).
- Sau đó set `published=True` trên Shopify.
- Nếu thành công sẽ in: `✅ Stripped generic + published and marked done: 691791954238`.

## Cách 2: fix_published_generic + publish-id

Nếu bài **đã published** nhưng vẫn còn generic:

```bash
cd "Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory"
python scripts/fix_published_generic.py 691791954238
cd pipeline_v2
python ai_orchestrator.py publish-id 691791954238
```

(Lệnh 1 cập nhật body_html, lệnh 2 chỉ set published nếu cần; thường chỉ cần lệnh 1 vì bài đã live.)

## Pipeline đã cập nhật

- **Sau meta fix**: luôn gọi `_strip_generic_before_publish(article_id)` trước gate → mọi bài đều được strip generic trước khi review/publish.
- **strip-and-publish**: one-off cho 1 ID (strip rồi publish).
