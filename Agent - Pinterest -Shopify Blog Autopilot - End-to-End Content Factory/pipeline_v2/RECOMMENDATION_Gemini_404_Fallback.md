# Recommendation: Gemini Vision 404 – Ai Orchestrator & ReconcileGPT View

**Context:** Local runner chạy queue-run, generate AI images (Pollinations/Lexica) → gửi sang Gemini Vision để review (hands/people) → **Gemini API trả 404** → mọi ảnh bị reject → không có featured image → pipeline dừng.

---

## 1. Root cause (Ai Orchestrator phân tích)

**File:** `fix_images_properly.py`

```python
def is_vision_safe(result) -> bool:
    if result is None:      # ← Gemini 404 → vision_review trả None
        return False        # ← Treat như "unsafe" → REJECT ảnh
```

- Khi **Gemini trả 404**, `vision_review_image_gemini()` trả `None`
- `is_vision_safe(None)` = `False` → ảnh bị reject
- **Hiện tại:** "vision lỗi" = "ảnh không an toàn" (sai logic)
- **Đúng hơn:** "vision lỗi" = "bỏ qua vision, chấp nhận ảnh" (fail-open)

---

## 2. ReconcileGPT góc nhìn (chọn 1 mặt trận)

- **Bất lợi hiện tại:** Pipeline bị chặn bởi phụ thuộc Gemini, trong khi:
  - Pollinations/Lexica tạo ảnh OK
  - 404 có thể do: key sai, model deprecated, quota, region

- **Wedge:** Thắng ở **"có bài publish được"** trước, rồi mới tối ưu vision.

- **Barbell:**
  - **An toàn:** Khi vision fail → accept ảnh (để pipeline chạy tiếp)
  - **Sau:** Bật lại vision khi Gemini ổn định

---

## 3. Hành động đề xuất

### Option A: Fail-open khi vision lỗi (ưu tiên)

**Sửa `fix_images_properly.py` – `is_vision_safe` hoặc chỗ gọi:**

Khi `vision_result is None` (API lỗi) → **coi là pass**, không reject ảnh.

```python
def is_vision_safe(result) -> bool:
    if result is None:
        return True   # API down → fail-open, accept image
    if result.get("has_hands") or result.get("has_people"):
        return False
    if result.get("safe") is False:
        return False
    return True
```

**Tác dụng:** Pipeline chạy tiếp ngay cả khi Gemini 404.

---

### Option B: Tắt vision tạm thời

- `VISION_REVIEW=0` trong `.env` hoặc khi gọi `fix_images_properly`
- Ai_orchestrator đang set `VISION_REVIEW=1` khi gọi `_run_fix_images` → cần đổi sang `0` hoặc đọc từ env

**Ưu:** Không sửa logic, chỉ config.  
**Nhược:** Mất hẳn vision review đến khi bật lại.

---

### Option C: Kiểm tra Gemini API

- Kiểm tra `GEMINI_API_KEY` hợp lệ, quota, region
- Có thể model `gemini-1.5-flash` đã đổi/không dùng được → thử endpoint/model khác

---

## 4. Kết luận

| Agent              | Đề xuất                                                  |
|--------------------|----------------------------------------------------------|
| **Ai Orchestrator**| Option A – sửa `is_vision_safe` fail-open khi `result is None` |
| **ReconcileGPT**   | Ưu tiên "có bài publish" trước; vision là bước sau       |

**Thứ tự thực hiện gợi ý:**
1. Áp dụng Option A (fail-open)
2. Nếu cần nhanh: Option B (tắt vision tạm)
3. Sau khi pipeline chạy ổn: Option C (debug Gemini)
