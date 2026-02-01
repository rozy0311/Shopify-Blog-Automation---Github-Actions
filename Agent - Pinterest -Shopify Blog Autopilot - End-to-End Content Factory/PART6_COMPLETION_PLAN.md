# Part 6 Completion Plan - Auto Fix Sequential Every 10 Minutes

**Confidence: 90%** – Dựa trên phân tích Part 6 transcript và workflow hiện tại.

---

## Vấn đề chính (Part 6 kết thúc)

**User:** "chưa thấy workflow này Auto Fix Sequential (mỗi 10 phút)"

**Nguyên nhân (CTO Analysis):**
1. **Schedule chỉ chạy trên default branch** – Workflow có `cron: "*/10 * * * *"` nhưng GitHub chỉ trigger schedule từ workflow file trên default branch (thường `main` hoặc branch được set làm default trong repo settings).
2. **Workflow trên nhánh copilot** – File `.github/workflows/auto-fix-sequential.yml` đang ở nhánh `copilot/vscode-mk1uh8fm-4tpw`, chưa merge vào default.
3. **Heartbeat có thể skip** – Nếu `local_heartbeat.json` được push liên tục (timestamp < 15 phút), GHA sẽ skip mỗi lần chạy.

---

## Giải pháp (ReconcileGPT Decision)

### **Option A: Merge vào default branch (Recommended)**

**Pros:**
- Schedule tự chạy mỗi 10 phút
- Không cần can thiệp thủ công
- Đúng với yêu cầu "tự động 24/7"

**Cons:**
- Rủi ro: nếu workflow có lỗi → chạy mỗi 10 phút và fail liên tục
- Cần monitoring để phát hiện sớm

**Action:**
1. Xác định default branch của repo (check GitHub repo settings)
2. Merge `copilot/vscode-mk1uh8fm-4tpw` → default branch
3. Verify workflow xuất hiện trong Actions tab
4. Monitor 2-3 lần chạy đầu tiên (30 phút)

### **Option B: Trigger thủ công + Task Scheduler local**

**Pros:**
- Kiểm soát cao hơn
- Không ảnh hưởng default branch

**Cons:**
- Cần máy local luôn bật
- Không đúng với yêu cầu "không cần mở máy"

---

## Implementation Steps (Option A - Recommended)

### **Bước 1: Xác định default branch**

**Confidence: 80%** – Dựa trên git status, có thể là `feat/l6-reconcile-main` hoặc `main`.

**Cách kiểm chứng:**
```bash
gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'
```

### **Bước 2: Merge workflow vào default branch**

**Confidence: 85%** – Workflow đã được test và chạy thành công khi trigger thủ công.

**Commands:**
```bash
cd "D:\active-projects\Auto Blog Shopify NEW Rosie\Shopify Blog Automation - Github Actions"
git checkout <default-branch>
git merge copilot/vscode-mk1uh8fm-4tpw
git push origin <default-branch>
```

**Cách kiểm chứng:** GitHub → Actions → xem workflow "Auto Fix Sequential" xuất hiện và có schedule icon.

### **Bước 3: Verify schedule chạy**

**Confidence: 75%** – Schedule có thể mất 5-10 phút để trigger lần đầu.

**Cách kiểm chứng:**
- Đợi 15 phút sau khi merge
- Check GitHub Actions → xem có run mới với trigger "schedule" không
- Nếu không có → check heartbeat (có thể đang skip)

### **Bước 4: Setup monitoring**

**Confidence: 70%** – Cần thêm alert khi workflow fail liên tục.

**Options:**
1. **GitHub Actions notification** (Settings → Notifications → Actions)
2. **Supervisor workflow** (đã có trong Part 6) – monitor health và disable khi unstable
3. **Decision log** – chạy `reconcile_decision.py` định kỳ để update recommendation

---

## Bổ sung từ ReconcileGPT Framework

### **1. Memory Layer (State Management)**

**Thiếu:** Không có cách dễ dàng để xem "workflow đã chạy bao nhiêu bài, pass rate là bao nhiêu".

**Bổ sung:**
- Script `pipeline_v2/workflow_stats.py` – đọc workflow runs (qua GitHub API), tổng hợp pass/fail/publish → ghi vào `config/workflow_stats.json`
- Chạy định kỳ (mỗi giờ hoặc mỗi ngày) để có dashboard đơn giản

### **2. Cost Tracking (Optional)**

**Thiếu:** Không track token/API usage.

**Bổ sung (nếu cần):**
- Log usage mỗi run (Gemini tokens, Pollinations calls)
- Tổng hợp theo ngày/tuần
- Alert khi vượt budget

### **3. Human-in-the-Loop Checkpoints**

**Đã có:** Decision log, supervisor disable khi unstable.

**Bổ sung:**
- Runbook rõ hơn: "Khi nào review decision log", "Khi nào bật lại publish sau pause"
- Alert khi decision = `pause_and_review` (Slack/Email/Issue)

---

## Next Actions (Priority Order)

| Priority | Action | Confidence | Cách kiểm chứng |
|----------|--------|------------|-----------------|
| **P0** | Merge workflow vào default branch | 85% | GitHub Actions tab có workflow với schedule icon |
| **P1** | Verify schedule chạy (đợi 15-20 phút) | 75% | Có run mới với trigger "schedule" |
| **P2** | Setup heartbeat monitoring | 70% | Alert khi heartbeat quá cũ (nếu expect local chạy) |
| **P3** | Add workflow_stats.py (memory layer) | 65% | File `config/workflow_stats.json` được update định kỳ |
| **P4** | Enhance decision log với alert | 60% | Slack/Issue notification khi pause_and_review |

---

## Files Created/Updated

1. ✅ **AUTO_ACTIONS_DONE.md** – giải thích vì sao không thấy workflow chạy
2. ✅ **config/decision_log.json** – thêm next_action, recommendation
3. ✅ **run_local_queue.ps1** – thêm push heartbeat khi `LOCAL_HEARTBEAT_PUSH=true`
4. ✅ **.github/workflows/auto-fix-sequential.yml** – thêm workflow_dispatch inputs (fix_max_items, skip_heartbeat)
5. ✅ **NEXT_AFTER_PART6.md** – update với "Đã làm tự động"
6. 🆕 **PART6_COMPLETION_PLAN.md** (file này) – roadmap hoàn thiện Part 6

---

## Tóm tắt cho user

**Đã làm:**
- ✅ Workflow có schedule mỗi 10 phút
- ✅ Local runner có push heartbeat (optional)
- ✅ Decision log có next_action
- ✅ Workflow có inputs để trigger thủ công

**Còn thiếu:**
- ⏳ Merge workflow vào default branch (để schedule chạy)
- ⏳ Verify schedule chạy thực tế
- ⏳ Monitoring/alert (optional nhưng recommended)

**User có thể làm ngay:**
```bash
# 1. Xác định default branch
gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'

# 2. Merge vào default
git checkout <default-branch>
git merge copilot/vscode-mk1uh8fm-4tpw
git push origin <default-branch>

# 3. Đợi 15 phút, check GitHub Actions tab
```
