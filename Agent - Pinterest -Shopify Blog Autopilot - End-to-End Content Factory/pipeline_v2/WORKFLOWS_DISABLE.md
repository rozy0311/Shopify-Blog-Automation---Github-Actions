# Workflows cần disable (tránh conflict)

Để Auto Fix Sequential chạy ổn định, nên **disable** các workflow sau trên GitHub:

| Workflow | Lý do |
|----------|-------|
| **Meta-Agent Autonomous Worker** | Chạy mỗi 6h, overlap với Auto Fix Sequential, dễ conflict khi cùng sửa articles |
| **re-audit** | Chạy mỗi 6h, chỉ audit (không fix) – có thể giữ nếu cần monitor; nếu hay fail thì disable |

**Cách disable:** GitHub → Actions → chọn workflow → "..." → Disable workflow

**Giữ enabled:**
- **Auto Fix Sequential** – main workflow fix + publish
- **Auto Fix Manual Trigger** – chạy thủ công khi cần
- **Article Pre-Publish Review** – review 1 bài thủ công
- **Copilot code review** – review code
