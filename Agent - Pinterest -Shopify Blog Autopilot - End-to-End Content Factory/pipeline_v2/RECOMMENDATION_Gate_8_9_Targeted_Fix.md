# ReconcileGPT: Gate 8-9/10 – Targeted Fix vs Rebuild

## 1. Vấn đề

- Articles đạt 8–9/10 (thiếu 1–2 check) → **không publish**
- `_auto_fix_article` trả về `EVIDENCE_REBUILD_REQUIRED` khi có Missing sections / Generic / Low sources → **bỏ qua** image fix và các fix khác
- Meta fix (run_meta_fix_queue) đã chạy nhưng nhiều bài vẫn thiếu table, blockquotes, sources

## 2. Phân tích (ReconcileGPT)

| Vai trò | Phân tích |
|---------|-----------|
| **CTO** | Thiếu path fix có chọn lọc. Gate có 10 checks; với 8–9/10 thì chỉ còn 1–2 checks fail. Cần fix đúng các checks đó thay vì rebuild toàn bộ. |
| **COO** | EVIDENCE_REBUILD_REQUIRED khiến pipeline bị block, không có fallback khi gần pass (8–9/10). |
| **ReconcileGPT** | Ưu tiên **targeted fix** cho 8–9/10 trước khi retry: inject table, blockquotes, sources dựa trên checks thất bại. |

## 3. Giải pháp đã áp dụng

1. **`_targeted_gate_fix(article_id, checks)`** – inject theo checks thất bại:
   - `tables_min` fail → `_inject_table()`
   - `blockquotes_min` fail → `_inject_blockquotes()`
   - `sources_min` fail → `_inject_sources_fallback()`
   - `no_generic_or_contamination` fail → `_remove_generic_sections()`
   - `meta_description` fail → `_ensure_meta_description()`
   - `images_unique` fail → `_run_fix_images()`

2. **Flow mới khi gate fail (7–9/10)**:
   - Gọi `_targeted_gate_fix` trước
   - Re-audit
   - Nếu gate pass → pre_publish_review → publish
   - Nếu vẫn fail → fallback sang `_auto_fix_article` và retry

3. **Injection trực tiếp** trong `ai_orchestrator` – dùng `self.api.update_article`, không subprocess.

## 4. Nguyên tắc

- **Targeted fix trước rebuild** – fix đúng checks thiếu thay vì rebuild
- **Log checks thất bại** – `Failing checks: tables_min, blockquotes_min` để debug
- **Wedge** – ưu tiên “có bài publish” với chất lượng chấp nhận được (8–9/10 nếu targeted fix thành công)
