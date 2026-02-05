# Recommendation: Generic Content in Published Blogs – Ai Orchestrator & ReconcileGPT

**Context:** Bài blog vừa publish vẫn còn generic content. Cần chặn ở pipeline và sửa bài đã live.

---

## 1. Đã thực hiện (Ai Orchestrator + ReconcileGPT)

### A) Pre-publish strip
- **File:** `ai_orchestrator.py`
- **Thay đổi:** Gọi `_strip_generic_before_publish()` trước mỗi `_publish_to_shopify()`
- **Hành vi:** Trước khi publish, lấy article → strip generic qua `_remove_generic_sections` → cập nhật body nếu thay đổi → rồi mới publish

### B) Sync GENERIC_PHRASES
- Thêm `"it's important to remember"`, `"it is important to remember"` vào ai_orchestrator
- Đồng bộ với `pre_publish_review.py`

### C) Xóa duplicate GENERIC_SECTION_HEADINGS
- Xóa block trùng lặp trong ai_orchestrator

---

## 2. Bài đã publish có generic

**Script:** `scripts/fix_published_generic.py`

**Chạy khi đã cấu hình đúng Shopify (.env / SHOPIFY_SHOP dạng `store.myshopify.com`):**

```powershell
cd scripts

# Xem sẽ sửa bài nào (dry-run)
python fix_published_generic.py --all --dry-run

# Sửa tất cả bài published
python fix_published_generic.py --all

# Hoặc sửa từng ID
python fix_published_generic.py 690495881534 690497126718
```

**Lưu ý:** `SHOPIFY_SHOP` phải đủ domain (vd: `the-rike-inc.myshopify.com`), không chỉ `the-rike-inc`.

---

## 3. Flow publish mới

1. Gate pass / auto-fix pass  
2. Pre-publish review pass  
3. **→ `_strip_generic_before_publish()`** (mới)  
4. → Publish

Mọi lối publish qua `_publish_to_shopify` đều được strip trước khi lên live.
