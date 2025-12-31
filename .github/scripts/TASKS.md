# Autonomous Agent Task Templates

Đây là các template để định nghĩa task cho Autonomous GitHub Worker.

---

## Format chuẩn

```yaml
name: task-name
description: Mô tả ngắn
schedule: "0 */6 * * *"  # Cron expression
businessPrompt: |
  [Business task description]
  
  Context:
  - Business background: <mô tả bối cảnh>
  - Goal: <mục tiêu cụ thể>
  - Input: <file/folder nguồn>
  - Output: <file/báo cáo mong muốn>
  
  Constraints:
  - Allowed paths: <paths được phép>
  - Forbidden paths: <paths cấm>
  - Risk / safety notes: <ghi chú an toàn>
  
  Checks:
  - <lệnh kiểm tra 1>
  - <lệnh kiểm tra 2>
```

---

## Task có sẵn

### 1. update-report
Cập nhật REPORT.md với thống kê mới nhất.

### 2. cleanup-logs
Dọn dẹp log files cũ hơn 7 ngày.

---

## Thêm task mới

1. Edit file `.github/scripts/autonomous-agent.mjs`
2. Thêm task vào `DEFAULT_TASKS` array
3. Implement handler trong `executeTask()` function

---

## Chạy thủ công

1. Vào GitHub repo → Actions → "Autonomous GitHub Worker"
2. Click "Run workflow"
3. Nhập task name (optional)
4. Click "Run workflow"

---

## Lưu ý an toàn

- Agent **CHỈ** modify được paths trong `allowedPaths`
- Agent **KHÔNG BAO GIỜ** touch `forbiddenPaths`
- Mọi thay đổi đều được log
- Nếu checks fail → không commit

---

## Logs

Logs được lưu tại `logs/agent-run-*.log`
