# Runbook – Shopify Blog Autopilot

## Biến điều khiển (GitHub Actions Variables)

| Biến | Ý nghĩa | Mặc định / Gợi ý |
|------|---------|-------------------|
| `WF_ENABLED` | Bật/tắt pipeline tự động (schedule + supervisor dispatch) | `false` (dry-run) |
| `ALLOW_PUBLISH` | Cho phép publish thật lên Shopify (`human_enabled`) hay chỉ review/draft (`human_disabled`) | `human_disabled` |
| `LOCAL_HEARTBEAT_FILE` | File heartbeat trong repo (local runner ghi) | `local_heartbeat.json` |
| `LOCAL_HEARTBEAT_URL` | URL raw file heartbeat (nếu dùng URL thay vì file trong repo) | (trống) |
| `LOCAL_HEARTBEAT_MAX_AGE_MINUTES` | Heartbeat còn "mới" trong bao nhiêu phút thì Actions skip executor | `15` |

---

## Khi nào bật publish

1. **Chỉ bật `ALLOW_PUBLISH=human_enabled`** khi:
   - Bạn đã kiểm tra vài bài draft (review mode) ổn (SEO, hình, nguồn).
   - Queue (Google Sheet) đã sẵn sàng, không có dữ liệu test lỗi.
   - Bạn chấp nhận rủi ro bài tự động publish lên blog.

2. **Bật `WF_ENABLED=true`** khi:
   - Bạn muốn supervisor tự dispatch (review hoặc publish) theo schedule (30 phút).
   - Bạn đã cấu hình Sheets, secrets (Shopify, LLM, Google, Slack nếu dùng).

3. **Khuyến nghị**: Luôn bắt đầu với `WF_ENABLED=true`, `ALLOW_PUBLISH=human_disabled` (chỉ review/draft). Sau khi xác nhận ổn mới chuyển `ALLOW_PUBLISH=human_enabled`.

---

## Khi incident được mở (Supervisor disable pipeline)

Supervisor mở incident khi **≥2 run thất bại** gần đây (workflow `publish.yml`). Khi đó nó sẽ:

- Set `WF_ENABLED=false`, `ALLOW_PUBLISH=human_disabled`.
- Tạo GitHub Issue với label `incident` + severity.
- Gửi thông báo qua Slack (nếu đã cấu hình `SLACK_WEBHOOK`).

**Bạn nên làm:**

1. Mở GitHub Issues, tìm issue mới nhất label `incident`.
2. Xem link các run thất bại trong nội dung issue → kiểm tra log từng run (lỗi API, secret, config, v.v.).
3. Sửa lỗi (code/config/secrets).
4. Chạy thử workflow `Shopify Blog Executor` bằng **workflow_dispatch** với mode `review` để xác nhận ổn.
5. Khi đã ổn: vào **Settings → Actions → Variables** và bật lại:
   - `WF_ENABLED` = `true`
   - `ALLOW_PUBLISH` = `human_enabled` hoặc `human_disabled` tùy chính sách.

---

## Heartbeat (local runner)

- **Nếu chạy executor local** (PowerShell: `scripts/run_local_executor.ps1` hoặc shell: `scripts/run_local_executor.sh`): script sẽ ghi `local_heartbeat.json` trước khi chạy. Nếu bạn set `LOCAL_HEARTBEAT_PUSH=true` (và repo có commit/push), file heartbeat trên repo sẽ được cập nhật.
- **Trên GitHub Actions**: mỗi lần chạy `publish.yml`, nó đọc heartbeat. Nếu heartbeat **còn mới** (trong vòng `LOCAL_HEARTBEAT_MAX_AGE_MINUTES`) → **bỏ qua** bước chạy executor (tránh chạy đôi local + cloud).
- **Nếu bạn mong đợi local chạy định kỳ** mà heartbeat lâu không cập nhật: có thể local runner đã dừng hoặc lỗi; nên có alert (Slack/Issue) khi heartbeat quá cũ (xem NEXT_AFTER_PART6.md).

---

## Local runner & GitHub workflow chạy mượt

- **SETUP_BEFORE_FIRST_RUN.md** – Checklist một lần trước khi chạy local hoặc GHA lần đầu (repo root, .env, secrets/vars, commit/push).
- **LOCAL_RUNNER_AND_WORKFLOW.md** – Chạy local từ repo root, heartbeat, tránh chạy đôi với Actions, checklist và lỗi thường gặp.

---

## Liên hệ / Mở rộng

- Chi tiết pipeline: `PIPELINE_README.md`.
- Bước tiếp theo sau Part 6: `NEXT_AFTER_PART6.md`.
- Prompt gọi agent session mới: `PROMPT_SESSION_MOI_Shopify_Blog_Autopilot.txt`.
