# GitHub Workflows – Nên bật / chạy cái nào

Danh sách workflow trong repo và gợi ý **bật (enable)** / **chạy (run)**.

---

## Workflow chính cho pipeline blog (Part 6)

| Workflow (tên trong GitHub) | File | Chức năng | Nên bật? | Chạy khi nào |
|-----------------------------|------|-----------|----------|--------------|
| **Shopify Blog Executor** | `publish.yml` | Đọc queue (Sheets) → LLM → Shopify; check heartbeat; chạy executor. | **Có** – đây là workflow **chính** chạy pipeline (không phải “cũ” deprecated). | Schedule mỗi 10 phút **hoặc** Run workflow (workflow_dispatch) với mode `review` / `publish`. |
| **Shopify Blog Supervisor** | `supervisor.yml` | Kiểm tra queue + pipeline health mỗi 30 phút → dispatch **Shopify Blog Executor** (review hoặc publish) hoặc disable khi unstable. | Tuỳ chọn – bật nếu muốn **tự động** dispatch theo queue/health; không bật nếu chỉ chạy Executor tay hoặc schedule. | Schedule 30 phút hoặc Run workflow. |

**Nếu “Shopify Blog Executor” đang bị disable:**

1. Vào **GitHub → repo → Actions**.
2. Sidebar trái: chọn **Shopify Blog Executor**.
3. Nếu thấy **“This workflow is disabled”** → bấm **“Enable workflow”** (hoặc I understand, Enable workflow).
4. Sau khi bật:
   - **Chạy tay**: **Run workflow** → chọn mode `review` (an toàn) hoặc `publish` → Run.
   - **Chạy theo schedule**: Đảm bảo biến **WF_ENABLED** = `true` (Settings → Secrets and variables → Actions → Variables). Nếu `false` thì schedule vẫn chạy nhưng mode sẽ là review (trừ khi dispatch từ Supervisor).

---

## Workflow phụ (dùng khi cần)

| Workflow | File | Chức năng | Bật / chạy |
|----------|------|-----------|------------|
| **Article Pre-Publish Review** | `article-review.yml` | Review **một bài** (article_id) trước khi publish; có thể auto-fix rồi review lại. | Chỉ `workflow_dispatch` – bật, chạy khi cần review 1 bài cụ thể. |
| **Auto Fix Sequential (1 article)** | `auto-fix-sequential.yml` | Fix tuần tự 1 bài. | Có schedule + dispatch – bật nếu dùng; chạy tay khi cần fix 1 bài. |
| **Auto Fix Manual Trigger** | `auto-fix-manual.yml` | Fix theo kích hoạt tay. | Chỉ dispatch – bật, chạy khi cần. |
| **re-audit** | `re-audit.yml` | Audit lại (re-audit). | Có schedule + dispatch – bật nếu dùng. |
| **Meta-Agent Autonomous Worker** | `autonomous-agent.yml` | Agent tự chạy task. | Tuỳ dự án. |
| **Copilot Coding Agent** / **Auto-Assign Copilot Coding Agent** | `copilot-agent.yml`, `openhands-resolver.yml` | Dùng cho coding agent. | Tuỳ dự án, không bắt buộc cho blog pipeline. |

---

## Tóm tắt: “Giờ thì làm gì”

1. **Bật lại Shopify Blog Executor** (Actions → Shopify Blog Executor → Enable workflow).
2. (Tuỳ chọn) Bật **Shopify Blog Supervisor** nếu muốn tự động dispatch theo queue/health.
3. Kiểm tra **Variables**: `WF_ENABLED`, `ALLOW_PUBLISH` (xem RUNBOOK.md). Khuyến nghị lúc mới: `WF_ENABLED=true`, `ALLOW_PUBLISH=human_disabled` (chỉ review/draft).
4. **Chạy thử**: Actions → Shopify Blog Executor → **Run workflow** → mode `review` → Run. Xem log để đảm bảo không lỗi secrets/vars.

Sau khi Executor bật và chạy thử ổn, pipeline (schedule hoặc Supervisor) sẽ chạy bình thường.
