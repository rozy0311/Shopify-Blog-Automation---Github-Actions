# Chạy executor: Local (1) và GitHub Actions (2)

## Cách 1: Chạy local (cần cài Node.js)

Local runner cần **Node.js** và **npm** để build và chạy executor.

### Cài đặt Node.js

1. Tải Node.js LTS (khuyến nghị v20 hoặc mới hơn):  
   https://nodejs.org/en/download/

2. Chạy installer, chọn "Add to PATH" (mặc định đã bật).

3. Sau khi cài xong, **đóng và mở lại PowerShell** để PATH cập nhật.

4. Kiểm tra:
   ```powershell
   node --version
   npm --version
   ```
   Nếu hiện version (vd. `v20.x.x`, `10.x.x`) là OK.

---

## Sau khi cài Node.js

Chạy local runner:

```powershell
cd "D:\active-projects\Auto Blog Shopify NEW Rosie\Shopify Blog Automation - Github Actions"
.\scripts\run_local_executor.ps1 -Mode review
```

Lần đầu sẽ chạy `npm ci` (cài dependencies) và build executor; đợi vài phút. Sau đó executor sẽ chạy.

---

---

## Cách 2: Chạy trên GitHub Actions (không cần Node.js trên máy)

1. Vào repo trên GitHub → **Actions** → **Shopify Blog Executor** (workflow `publish.yml`).
2. Nếu workflow đang disabled: **Settings** → **Actions** → **General** → Allow workflows.
3. **Run workflow** → chọn branch (vd. `feat/l6-reconcile-main` hoặc `main`) → mode `review` → **Run workflow**.
4. Secrets/variables cần cấu hình trong repo: **Settings** → **Secrets and variables** → **Actions** (xem `SETUP_BEFORE_FIRST_RUN.md` trong thư mục Agent).
