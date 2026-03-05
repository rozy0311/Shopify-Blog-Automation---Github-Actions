# 2026-03 Agent Training Pack

## 📊 Phân tích bài toán
- Automation Score: 8/12
  - Data sources: 4/4 (nhiều nguồn web + trend + docs)
  - Logic complexity: 3/4 (memory + HITL + orchestration)
  - Integration points: 1/4 (chủ yếu local repo hiện tại)
- Risk Level: 🔴 (do có thể dẫn đến tự động hóa mạnh nếu bật tool execution rộng)

## Mục tiêu
- Chuẩn hóa kiến thức từ các link mới thành tài liệu training áp dụng ngay.
- Tiếp tục hướng local-first, permission-first, memory continuity.
- Tạo checklist cài đặt + template prompt để train agent ổn định.

## Cấu trúc
- `SOURCE_DIGEST.md`: tóm tắt nguồn và insight áp dụng.
- `TRAINING_ROADMAP.md`: roadmap 4 tuần để tiếp tục training.
- `INSTALL_PLAYBOOK.md`: playbook cài đặt/enable tính năng.
- `templates/`: prompt + schema để chạy agent có memory/HITL.
- `scripts/`: script khởi tạo môi trường và vòng memory cycle demo.

## Nguyên tắc áp dụng
1. `ReconcileGPT` chỉ phân tích trade-off, không tự quyết định hành động rủi ro.
2. Bất kỳ tác vụ có ghi/xóa dữ liệu thật phải có human approval.
3. Ưu tiên memory quan sát (observational log) trước khi chuyển sang RAG nặng.
4. Giữ local-first; secrets chỉ đặt trong `.env` hoặc secret store.

## Quick start
1. Mở `INSTALL_PLAYBOOK.md` và chạy theo thứ tự.
2. Dùng `templates/system_prompt_memory_hitl.md` cho orchestrator.
3. Chạy `scripts/run_memory_cycle.py` để test vòng nén memory.
4. Dùng `TRAINING_ROADMAP.md` để triển khai theo tuần.
