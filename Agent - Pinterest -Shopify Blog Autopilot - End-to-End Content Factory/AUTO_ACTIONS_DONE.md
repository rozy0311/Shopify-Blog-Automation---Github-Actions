# Tự động làm theo ý agent (sau Part 6)

Tài liệu này ghi lại các việc agent đã tự làm và hướng dẫn để **Auto Fix Sequential** chạy đúng mỗi 10 phút.

---

## Đã kiểm tra và xác nhận

### 1. Workflow Auto Fix Sequential (`.github/workflows/auto-fix-sequential.yml`)

- **Schedule:** `cron: "*/10 * * * *"` → chạy mỗi 10 phút (UTC).
- **Trigger tay:** `workflow_dispatch: {}` → có thể bấm "Run workflow" trên GitHub Actions.
- **Heartbeat:** Job `heartbeat-check` đọc `local_heartbeat.json` (từ checkout). Nếu timestamp < 15 phút → skip job `auto-fix-one` (tránh chạy đôi với local).
- **Queue:** Dùng `queue-run` (meta fix → gate 9/10 → targeted fix → pre_publish_review → publish).
- **Working directory:** Các bước dùng `Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory/pipeline_v2` → **đúng khi repo root là repo cha** (Shopify Blog Automation - Github Actions).

### 2. Local runner (`run_local_queue.ps1`)

- Ghi **heartbeat** vào `local_heartbeat.json` tại **thư mục cha của Content Factory** (repo root nếu repo là repo cha).
- Mỗi iteration: update heartbeat → chạy `ai_orchestrator.py queue-run` → đợi DelaySeconds → lặp lại.
- **Để GHA skip khi máy local đang chạy:** Cần **push** file `local_heartbeat.json` lên repo (GHA đọc từ checkout). Nếu không push, GHA không thấy heartbeat mới → vẫn chạy mỗi 10 phút.

### 3. Decision log (`config/decision_log.json`)

- Đang ghi `pause_and_review` khi log chỉ có bản ghi fail (review_pass = 0). Theo `DECISION_LOG_README.md`, điều này có thể bình thường nếu `anti_drift_run_log.csv` chỉ ghi lần fail.
- Đã thêm `next_action` và `recommendation` để bước tiếp theo rõ ràng.

---

## Vì sao có thể “không thấy” Auto Fix Sequential chạy mỗi 10 phút?

| Nguyên nhân | Cách kiểm tra / xử lý |
|-------------|------------------------|
| **Workflow nằm trên nhánh không phải default** | GitHub chỉ chạy **schedule** trên **default branch**. Merge `.github/workflows/auto-fix-sequential.yml` vào default branch (vd. `main` hoặc `feat/l6-reconcile-main`). |
| **Repo đang mở là Content Factory (con)** | Schedule chạy ở **repo cha** (Shopify Blog Automation - Github Actions). Mở repo cha trên GitHub → Actions → xem workflow "Auto Fix Sequential (1 article)". |
| **Heartbeat luôn skip** | Nếu local (hoặc máy khác) push `local_heartbeat.json` liên tục trong 15 phút, GHA sẽ skip. Tạm không push heartbeat, hoặc tăng `LOCAL_HEARTBEAT_MAX_AGE_MINUTES` (vars) lên 5 để GHA ít bị skip. |
| **Workflow bị Disable** | GitHub → Actions → "Auto Fix Sequential (1 article)" → "..." → kiểm tra không bị **Disable workflow**. |
| **Queue trống / chưa init** | Workflow cần có `anti_drift_queue.json` (từ queue-init hoặc scan). Lần đầu có thể cần chạy **Scan issues** + **queue-init** (workflow đã có bước khi `needs_refresh == true`). |

---

## Việc bạn có thể làm ngay (không cần hỏi lại)

1. **Chạy local (từ thư mục Content Factory):**
   ```powershell
   .\run_local_queue.ps1 -MaxItems 3 -DelaySeconds 300
   ```
   → Ghi heartbeat tại repo root (thư mục cha). GHA sẽ skip nếu bạn **push** file đó lên.

2. **Trigger workflow tay (khi repo có workflow trên branch hiện tại):**
   - Vào GitHub → repo **Shopify Blog Automation - Github Actions** → Actions → "Auto Fix Sequential (1 article)" → "Run workflow".

3. **Để schedule chạy mỗi 10 phút:**
   - Đảm bảo file `auto-fix-sequential.yml` nằm trong **default branch** của repo (merge từ nhánh hiện tại vào default).
   - Sau đó chỉ cần đợi; không cần bấm gì thêm.

4. **Cập nhật decision / reconcile:**
   ```powershell
   cd pipeline_v2
   python reconcile_decision.py --last 50
   ```
   → Đọc 50 dòng gần nhất của run log → ghi lại `config/decision_log.json`.

---

## Tóm tắt

- **Auto Fix Sequential** đã cấu hình đúng: schedule 10 phút, heartbeat, queue-run.
- “Không thấy” thường do: workflow chưa trên default branch, hoặc đang xem nhầm repo/nhánh, hoặc heartbeat đang skip.
- Local: chạy `run_local_queue.ps1`; muốn GHA skip khi local chạy thì cần push `local_heartbeat.json` (hoặc dùng biến/vars heartbeat theo RUNBOOK).
