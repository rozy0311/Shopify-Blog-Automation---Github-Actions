# Trước lần chạy đầu – Local runner & GitHub Actions

Checklist một lần trước khi chạy **local runner** hoặc **workflow GitHub Actions** lần đầu.

---

## 1. Repo gốc (Shopify Blog Automation - Github Actions)

- **Local runner** và **workflow** nằm ở **repo root** (thư mục cha của thư mục Agent).
- Đường dẫn: `...\Shopify Blog Automation - Github Actions\` (có `.github\workflows\`, `scripts\run_local_executor.ps1`, `apps\executor`, `local_heartbeat.json`).

---

## 2. Chạy Local runner lần đầu

| Bước | Việc |
|------|------|
| 1 | Mở terminal tại **repo root** (không phải trong thư mục Agent). |
| 2 | Tạo file **`.env`** ở repo root với ít nhất: `CONFIG_FILE` hoặc `LLM_CONTROL_PROMPT`; và một trong `QUEUE_FILE` / `QUEUE_URL` / `SHEETS_ID`. (Xem `.env.example` nếu có.) |
| 3 | (Tuỳ chọn) Nếu muốn GHA **skip** khi local đang chạy: thêm `LOCAL_HEARTBEAT_PUSH=true` vào `.env`; hoặc cấu hình biến `LOCAL_HEARTBEAT_URL` trên GitHub. |
| 4 | Chạy: `.\scripts\run_local_executor.ps1 -Mode review` (PowerShell) hoặc `./scripts/run_local_executor.sh` (bash). |
| 5 | Lần đầu sẽ chạy `npm ci` và build executor; đợi xong rồi executor chạy. |

---

## 3. Chạy GitHub Actions workflow lần đầu

| Bước | Việc |
|------|------|
| 1 | Vào repo trên GitHub → **Settings → Secrets and variables → Actions**. |
| 2 | Thêm **Secrets** (bắt buộc): `SHOPIFY_ACCESS_TOKEN`, `GEMINI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON` (nếu dùng Sheets). (Các secret khác theo workflow: `SHOPIFY_SHOP`, `SHOPIFY_BLOG_ID`, `OPENAI_API_KEY` nếu dùng, v.v.) |
| 3 | Thêm **Variables**: `SHEETS_ID`, `SHEETS_RANGE`, `CONFIG_RANGE` (nếu dùng Sheets); `WF_ENABLED` = `false`, `ALLOW_PUBLISH` = `human_disabled` lúc mới. (Xem RUNBOOK.md.) |
| 4 | Chạy workflow: **Actions → Shopify Blog Executor → Run workflow** (mode `review`). Hoặc đợi schedule (mỗi 10 phút) nếu đã bật `WF_ENABLED=true`. |

---

## 4. Đã commit & push chưa?

- Các file mới/thay đổi trong **thư mục Agent** (NEXT_AFTER_PART6.md, LOCAL_RUNNER_AND_WORKFLOW.md, RUNBOOK.md, PROMPT_SESSION_MOI_Shopify_Blog_Autopilot.txt, config/decision_log.json, config/DECISION_LOG_README.md, pipeline_v2/reconcile_decision.py, SETUP_BEFORE_FIRST_RUN.md, v.v.) cần được **commit và push** lên GitHub nếu bạn muốn lưu và đồng bộ.
- Từ **repo root**:  
  `git add "Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory/"`  
  `git commit -m "Docs: Part 6 follow-up, runbook, decision log, reconcile, local+GHA checklist"`  
  `git push`

---

## 5. Còn cần bổ sung gì? (tuỳ chọn)

- **Alert heartbeat quá cũ**: Job/workflow kiểm tra heartbeat cũ hơn X phút → notify (Slack/Issue). Có thể thêm vào repo root sau.
- **Cost agent / Eval trend**: Log token/API, báo cáo chất lượng theo thời gian. Tuỳ nhu cầu.
- **Dashboard báo cáo**: Tổng hợp định kỳ (ngày/tuần) → Slack hoặc Issue. Tuỳ nhu cầu.

Sau khi xong bước 2 hoặc 3 trên là **có thể chạy** local hoặc GHA. Commit/push (bước 4) để lưu thay đổi lên GitHub.
