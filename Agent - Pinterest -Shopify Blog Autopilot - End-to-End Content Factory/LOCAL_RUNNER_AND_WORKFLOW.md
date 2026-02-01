# Local runner & GitHub Actions – Chạy mượt

Tài liệu này nằm trong **Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory**. Các lệnh và đường dẫn bên dưới là **từ thư mục gốc repo** (Shopify Blog Automation - Github Actions), tức thư mục cha của thư mục Agent.

---

## Checklist – Chạy mượt

### 1. Repo gốc và cấu trúc

- **Repo root**: `Shopify Blog Automation - Github Actions` (chứa `.github/workflows/`, `scripts/`, `apps/`, `local_heartbeat.json`).
- **Local runner**: chạy từ repo root. Không chạy từ trong thư mục Agent.

### 2. Trước khi chạy local

- [ ] Đã `cd` vào **repo root**.
- [ ] Có file **`.env`** ở repo root (hoặc đã set biến môi trường):
  - `CONFIG_FILE` hoặc `LLM_CONTROL_PROMPT`
  - `QUEUE_FILE` hoặc `QUEUE_URL` hoặc `SHEETS_ID`
  - (Tuỳ chọn) `LOCAL_HEARTBEAT_PUSH=true` nếu muốn push heartbeat lên repo để GHA skip khi local đang chạy.
- [ ] Đã chạy `npm ci` và `npm run --workspace apps/executor build` ít nhất một lần (script local đã gọi rồi nhưng lần đầu có thể lâu).

### 3. Chạy local (PowerShell, từ repo root)

```powershell
cd "D:\active-projects\Auto Blog Shopify NEW Rosie\Shopify Blog Automation - Github Actions"
.\scripts\run_local_executor.ps1 -Mode review
# hoặc -Mode publish (chỉ khi đã chủ động bật publish)
```

- Script sẽ:
  1. Load `.env`.
  2. Ghi **`local_heartbeat.json`** (timestamp) vào repo root.
  3. Nếu `LOCAL_HEARTBEAT_PUSH=true`: commit + push file heartbeat (để GHA đọc được và skip).
  4. Chạy executor: `node apps/executor/dist/index.js`.

### 4. Tránh chạy đôi (local + GHA)

- **Trên GHA**: workflow `publish.yml` mỗi lần chạy sẽ đọc `local_heartbeat.json` (từ checkout hoặc từ `LOCAL_HEARTBEAT_URL`). Nếu heartbeat **còn mới** (≤ `LOCAL_HEARTBEAT_MAX_AGE_MINUTES`, mặc định 15 phút) → **skip** bước chạy executor.
- **Để GHA “thấy” heartbeat khi bạn chạy local**:
  - **Cách 1**: Bật `LOCAL_HEARTBEAT_PUSH=true` và để script local commit/push `local_heartbeat.json`. GHA checkout repo mới nhất sẽ có file mới → skip khi local vừa chạy.
  - **Cách 2**: Dùng **`LOCAL_HEARTBEAT_URL`** (biến repo): local ghi heartbeat lên URL (vd. raw file trên repo khác, hoặc endpoint đơn giản), GHA đọc từ URL. Không phụ thuộc push từ local.

### 5. Biến GitHub (Settings → Actions → Variables)

| Biến | Gợi ý | Ghi chú |
|------|--------|---------|
| `WF_ENABLED` | `false` lúc mới | Bật `true` khi muốn schedule + supervisor tự chạy. |
| `ALLOW_PUBLISH` | `human_disabled` | Bật `human_enabled` chỉ khi đã review draft ổn. |
| `LOCAL_HEARTBEAT_FILE` | `local_heartbeat.json` | File trong repo (sau checkout). |
| `LOCAL_HEARTBEAT_URL` | (trống) hoặc URL raw | Nếu dùng URL thì GHA đọc heartbeat từ đây. |
| `LOCAL_HEARTBEAT_MAX_AGE_MINUTES` | `15` | Heartbeat “mới” trong 15 phút → GHA skip executor. |

### 6. Lỗi thường gặp

- **GHA vẫn chạy executor khi local đang chạy**: Heartbeat trên GHA là bản cũ (chưa push hoặc chưa có URL). Cần push heartbeat sau mỗi lần chạy local (Cách 1) hoặc cấu hình `LOCAL_HEARTBEAT_URL` (Cách 2).
- **Local báo thiếu CONFIG_FILE / QUEUE**: Thêm vào `.env` ở repo root: `CONFIG_FILE=...` hoặc `LLM_CONTROL_PROMPT=...`, và một trong `QUEUE_FILE` / `QUEUE_URL` / `SHEETS_ID`.
- **Supervisor tắt pipeline (WF_ENABLED=false)**: Khi ≥2 run `publish.yml` thất bại. Xử lý theo **RUNBOOK.md** (xem Issue incident, sửa lỗi, chạy thử review, rồi bật lại biến).

### 7. Khi nào coi là “chạy mượt”

- **Chỉ chạy local**: Local chạy xong không lỗi; heartbeat được ghi (và nếu dùng push/URL thì GHA thấy).
- **Chỉ chạy GHA**: Schedule hoặc dispatch chạy; không bị conflict với local nếu không chạy local cùng lúc.
- **Vừa local vừa GHA**: Một bên “sở hữu” tại một thời điểm – hoặc local chạy và push heartbeat → GHA skip; hoặc không chạy local → GHA chạy bình thường. Không có hai executor chạy song song cùng queue.

---

## Liên kết

- **RUNBOOK.md** – Biến điều khiển, khi nào bật publish, xử lý incident.
- **NEXT_AFTER_PART6.md** – Part 6 đã làm gì, việc tiếp theo, khi nào hoàn thành.
- **config/DECISION_LOG_README.md** – Decision log (reconcile); `pipeline_v2/reconcile_decision.py` ghi recommendation.
