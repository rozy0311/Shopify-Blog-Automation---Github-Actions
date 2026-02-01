# Nối tiếp Part 6 – Heartbeat & Tự động chạy

## Part 6 đã làm gì (tóm tắt)

**Part 6 – Thiết lập tự động chạy + Heartbeat** gồm:

1. **Executor trên GitHub Actions** (`publish.yml`)
   - Chạy theo **schedule** mỗi 10 phút (UTC) hoặc `workflow_dispatch`.
   - Mode: `review` (draft) hoặc `publish` (thật), điều khiển bởi `WF_ENABLED` / `ALLOW_PUBLISH`.

2. **Local heartbeat**
   - Script local: `scripts/run_local_executor.ps1` (Windows) hoặc `scripts/run_local_executor.sh` (Mac/Linux) ghi `local_heartbeat.json` với `timestamp` (Unix) + `iso` trước khi chạy executor.
   - Tùy chọn: `LOCAL_HEARTBEAT_PUSH=true` để commit/push heartbeat lên repo (hoặc dùng `LOCAL_HEARTBEAT_URL` trỏ tới URL raw file).

3. **Logic "tránh chạy đôi"**
   - Trong `publish.yml`, bước **Check local heartbeat**:
     - Đọc timestamp từ `LOCAL_HEARTBEAT_URL` hoặc `LOCAL_HEARTBEAT_FILE` (mặc định `local_heartbeat.json`).
     - Nếu heartbeat **còn mới** (trong vòng `LOCAL_HEARTBEAT_MAX_AGE_MINUTES`, mặc định 15 phút) → `LOCAL_HEARTBEAT_ACTIVE=true`.
     - Khi `LOCAL_HEARTBEAT_ACTIVE=true` → **bỏ qua** bước "Run executor" (tránh chạy đồng thời local + GitHub).

4. **Supervisor** (`supervisor.yml`)
   - Cron mỗi 30 phút (hoặc dispatch tay).
   - Đọc queue (Sheets), pipeline health (vài run gần nhất của `publish.yml`), biến `WF_ENABLED` / `ALLOW_PUBLISH`.
   - Nếu ≥2 run thất bại → disable pipeline (`WF_ENABLED=false`, `ALLOW_PUBLISH=human_disabled`), mở incident, notify human.
   - Nếu có pending và WF bật + publish enabled + có run review thành công gần đây → dispatch **publish**; ngược lại → dispatch **review** và notify.

---

## Bạn cần làm gì tiếp theo (sau Part 6)

Áp dụng tư duy **Multi-Agent Enterprise (ReconcileGPT)** vào pipeline Shopify Blog:

| Hạng mục | Mô tả ngắn | Trạng thái hiện tại | Hành động đề xuất |
|----------|------------|----------------------|--------------------|
| **Orchestrator / Supervisor** | Điều phối review vs publish, kill-switch | ✅ Đã có (supervisor + publish.yml) | Giữ, có thể bổ sung "reconcile" (xem dưới). |
| **Heartbeat & tránh double-run** | Local runner báo "đang chạy", Actions skip nếu heartbeat mới | ✅ Part 6 đã xong | Thêm **alert khi heartbeat quá cũ** (nếu bạn mong đợi local chạy định kỳ). |
| **Monitor / Validator** | KPI, thất bại, incident | ✅ Một phần: supervisor disable + openIncident + notifyHuman | Hoàn thiện: dashboard đơn giản hoặc report (Slack/Issue) mỗi ngày/tuần. |
| **Human-in-the-loop** | Chốt bật publish, review incident | ✅ ALLOW_PUBLISH=human_enabled, incident qua Issue | Ghi rõ runbook: "Khi nào bật publish", "Khi incident mở thì làm gì". |
| **Reconcile (decision engine)** | Tổng hợp review/auto-fix/publish → đề xuất quyết định | ⚠️ Chưa có lớp "reconcile" rõ | Mở rộng supervisor (hoặc job riêng): aggregate kết quả article-review, auto-fix, publish → output "recommendation" (enable/disable publish, cần human review bài X). |
| **Memory / State** | Lịch sử quyết định, queue, run outcomes | ⚠️ Một phần (Sheets, workflow runs) | Chuẩn hóa: lưu "last decision + reason" (ví dụ trong Sheets hoặc repo file) để Reconcile đọc lại. |
| **Cost (optional)** | Token/API theo run, budget | ❌ Chưa | Nếu cần: log usage mỗi run, so sánh với ngưỡng, alert (Slack/Issue). |
| **Eval / Quality** | Chất lượng bài (validator, reviewer) theo thời gian | ⚠️ Có validator + reviewer, chưa trend | Thêm bước tổng hợp: số bài pass/fail, lỗi lặp lại → báo cáo hoặc metric. |

---

## Luồng gợi ý (ReconcileGPT-style)

```
User/Policy (WF_ENABLED, ALLOW_PUBLISH)
         │
         ▼
+------------------+
| Supervisor       |  ← Đọc queue (Sheets), pipeline health, heartbeat (nếu thêm)
| (Orchestrator)   |
+------------------+
         │
         ├── [Unstable] → Disable + Incident + Notify
         ├── [No pending] → Skip
         ├── [WF off / Publish locked] → Dispatch review + Notify
         ├── [Chưa có review success gần đây] → Dispatch review + Notify
         └── [OK] → Dispatch publish + Notify
         │
         ▼ (optional)
+------------------+
| Reconcile layer  |  Aggregate: review results, fix results, publish outcomes
| (Decision log)   |  → Recommendation + persist "last decision" (Memory)
+------------------+
         │
         ▼
Human review (runbook, bật/tắt publish, xử lý incident)
```

---

## Việc ưu tiên làm ngay

1. **Alert heartbeat stale (optional nhưng hữu ích)**  
   Trong `publish.yml`, khi **skip vì heartbeat active**: log rõ. Khi **chạy executor** mà trước đó từng dùng local: có job nhỏ (schedule khác) kiểm tra "heartbeat cũ quá" so với kỳ vọng → notify (Slack/Issue).

2. **Runbook ngắn**  
   ✅ Đã có `RUNBOOK.md`: khi nào bật `ALLOW_PUBLISH=human_enabled`, khi incident mở thì check gì, ai được bật/tắt `WF_ENABLED`.

3. **Reconcile nhẹ + Decision log**  
   ✅ Đã làm:
   - **`config/decision_log.json`**: Lưu `last_decision` (continue_publish | pause_and_review | review_only | no_data), `reason`, `at`, `metrics`, `history`.
   - **`config/DECISION_LOG_README.md`**: Mô tả schema và ai ghi vào (script / Supervisor / human).
   - **`pipeline_v2/reconcile_decision.py`**: Đọc `anti_drift_run_log.csv` → đếm pass/fail → ghi recommendation vào `config/decision_log.json`. Chạy: `python pipeline_v2/reconcile_decision.py` (từ thư mục repo).
   - **`config/agent_memory.yaml`**: Đã thêm mục DECISION LOG tham chiếu file và script.

4. **PROMPT session mới**  
   ✅ Đã có `PROMPT_SESSION_MOI_Shopify_Blog_Autopilot.txt`.

---

## Tài liệu tham khảo

- **ReconcileGPT / EMADS-PR**: Sơ đồ Multi-Agent Enterprise (Orchestrator → Specialists → ReconcileGPT → Human Review → Execute → Monitor). Pipeline Shopify Blog đã có Orchestrator (supervisor), Execute (publish.yml + executor), Monitor (health + incident). Còn thiếu: Reconcile rõ ràng, Memory chuẩn hóa, Cost (tùy chọn), Eval trend.
- **LOCAL_RUNNER_AND_WORKFLOW.md**: Hướng dẫn local runner + workflow chạy mượt (repo root, heartbeat, checklist, lỗi thường gặp).
- **Workspace**: Repo root chứa `.github/workflows/` (publish, supervisor, …), `apps/executor/`, `apps/supervisor/`, `scripts/run_local_executor.*`, `local_heartbeat.json`; Agent folder chứa `pipeline_v2/`, `config/decision_log.json`, `reconcile_decision.py`.

---

## Khi nào coi là hoàn thành – Local runner & GHA chạy mượt

Các việc sau đã làm trong repo / Agent folder:

| Việc | Trạng thái | Ghi chú |
|------|------------|---------|
| Runbook (khi nào bật publish, xử lý incident) | ✅ | `RUNBOOK.md` |
| Prompt session mới | ✅ | `PROMPT_SESSION_MOI_Shopify_Blog_Autopilot.txt` |
| Decision log + Reconcile nhẹ | ✅ | `config/decision_log.json`, `reconcile_decision.py`, `config/DECISION_LOG_README.md` |
| Checklist local + GHA chạy mượt | ✅ | `LOCAL_RUNNER_AND_WORKFLOW.md` |
| Heartbeat tránh chạy đôi | ✅ | Part 6: `publish.yml` check heartbeat; local ghi + (tuỳ chọn) push hoặc `LOCAL_HEARTBEAT_URL` |
| Supervisor disable khi unstable | ✅ | `supervisor.yml` + notify + incident |

**Bạn coi là “chạy mượt” khi:**

1. **Chỉ local**: Chạy từ **repo root**: `.\scripts\run_local_executor.ps1 -Mode review`. Có `.env` (CONFIG_FILE hoặc LLM_CONTROL_PROMPT, QUEUE hoặc SHEETS_ID). Executor chạy xong không lỗi.
2. **Chỉ GHA**: Schedule hoặc workflow_dispatch chạy; không cần local. Biến `WF_ENABLED` / `ALLOW_PUBLISH` đã cấu hình đúng (xem RUNBOOK).
3. **Vừa local vừa GHA**: Một bên “sở hữu” tại một thời điểm: hoặc local chạy và push heartbeat (hoặc dùng `LOCAL_HEARTBEAT_URL`) → GHA skip; hoặc không chạy local → GHA chạy. Không có hai executor chạy song song. Chi tiết: **LOCAL_RUNNER_AND_WORKFLOW.md**.

**Chưa làm (tuỳ chọn):** Alert heartbeat quá cũ, Cost agent, Eval trend chất lượng bài, dashboard báo cáo định kỳ.
