# ReconcileGPT: GHA Workflow - Align với Local Runner

## 1. Vấn đề

- GHA publish vài blogs nhưng **gate không đạt** (pre_publish_review fail)
- Flow GHA khác flow local → kết quả không đồng nhất

## 2. Phân tích (ReconcileGPT)

| Vai trò | Phân tích |
|---------|-----------|
| **CTO** | GHA dùng custom loop (fix-ids → meta fix → review) thay vì queue-step. Thiếu: meta fix trước gate, targeted fix cho 7-9/10, gate 9/10 pass. |
| **COO** | Hai flow khác nhau → khó debug, không tận dụng logic local đã test. |
| **ReconcileGPT** | **Single source of truth**: GHA dùng cùng `queue-run` như local runner. |

## 3. Giải pháp đã áp dụng

### 3.1. Thay custom loop bằng `queue-run`

**Trước:**
```
fix-ids → build_meta_fix_queue → run_meta_fix_queue → pre_publish_review
→ nếu fail: force-rebuild-ids (2x) → queue-review fail
```

**Sau (giống local):**
```
queue-run $FIX_MAX_ITEMS --delay 0
→ meta fix first → audit (gate 9/10) → targeted fix (7-9) → review → publish
→ luôn retry, không manual_review
```

### 3.2. Cập nhật workflow

- `SHOPIFY_STORE_DOMAIN`: thêm cho format shop
- `MAX_QUEUE_RETRIES`: 20 (không manual review)
- Step "Run queue" gọi `ai_orchestrator.py queue-run`

### 3.3. Flow thống nhất

| Bước | Local | GHA |
|------|-------|-----|
| 1 | Meta fix (table, blockquotes, sources) | ✓ Cùng |
| 2 | Gate check (9/10 pass) | ✓ Cùng |
| 3 | Targeted fix nếu 7-9/10 | ✓ Cùng |
| 4 | pre_publish_review | ✓ Cùng |
| 5 | Publish hoặc retry | ✓ Cùng |

## 4. Nguyên tắc

- **Single flow**: GHA và local dùng cùng `ai_orchestrator.run_queue_once_with_backoff`
- **Gate 9/10**: Cho phép publish khi 1 check thiếu (sau targeted fix)
- **Sources/Quotes format**: Name — Description, expert name pattern (pre_publish_review)
