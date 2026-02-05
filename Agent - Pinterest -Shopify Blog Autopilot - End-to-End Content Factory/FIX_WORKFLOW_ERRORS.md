# Sửa lỗi workflow (áp dụng thủ công)

Hai lỗi bạn gặp và cách sửa:

---

## 1. Shopify Blog Executor – SyntaxError khi Check local heartbeat

**Nguyên nhân:** Trong `publish.yml`, lệnh `python -c "..."` dùng `\n` trong chuỗi; bash truyền literal `\n` vào Python nên Python báo lỗi.

**Cách sửa:** Mở file **`.github/workflows/publish.yml`** (ở **repo root** Shopify Blog Automation - Github Actions, không phải trong thư mục Agent).

Tìm bước **"Check local heartbeat"** và thay **hai dòng** `heartbeat_ts=$(python -c "..."` như sau:

**Dòng đọc từ URL** (khoảng dòng 125), thay:
```yaml
            heartbeat_ts=$(python -c "import json, os, urllib.request; url=os.environ.get('LOCAL_HEARTBEAT_URL','');\ntry:\n  resp=...
```
bằng:
```yaml
            heartbeat_ts=$(python3 -c 'import json,os,urllib.request; exec("try:\n r=urllib.request.urlopen(os.environ.get(\"LOCAL_HEARTBEAT_URL\",\"\"),timeout=10)\n d=json.loads(r.read().decode(\"utf-8\"))\n print(str(d.get(\"timestamp\",\"\")).strip())\nexcept Exception: pass")')
```

**Dòng đọc từ file** (khoảng dòng 128), thay:
```yaml
            heartbeat_ts=$(python -c "import json, os; path=os.environ.get('LOCAL_HEARTBEAT_FILE','local_heartbeat.json');\ntry:\n  data=json.load(open(path,'r',encoding='utf-8'))\n  print(str(data.get('timestamp','')).strip())\nexcept Exception:\n  print('', end='')\n")
```
bằng:
```yaml
            heartbeat_ts=$(python3 -c 'import json,os;f=os.environ.get("LOCAL_HEARTBEAT_FILE","local_heartbeat.json");d=json.load(open(f,"r",encoding="utf-8"));print(str(d.get("timestamp","")).strip())')
```

(Lưu ý: đổi `python` thành `python3` nếu runner dùng python3.)

---

## 2. auto-fix-sequential.yml – YAML syntax error line 245

**Nguyên nhân:** Trong YAML, tên step có dấu `:` (vd. "local: meta") nên parser hiểu nhầm là key/value.

**Cách sửa:** Mở **`.github/workflows/auto-fix-sequential.yml`** (repo root hoặc trong Agent tùy repo của bạn).

Tìm dòng 245:
```yaml
            - name: Run queue (same flow as local: meta fix, gate 9/10, targeted fix, review, publish)
```

Đổi thành (thêm dấu ngoặc kép cho `name`):
```yaml
            - name: "Run queue (same flow as local: meta fix, gate 9/10, targeted fix, review, publish)"
```

---

## 3. run_local_executor.ps1 không có trong thư mục Agent

Script **`run_local_executor.ps1`** nằm ở **repo root** (Shopify Blog Automation - Github Actions), trong thư mục **`scripts/`**, không nằm trong thư mục Agent.

**Cách chạy:** Mở terminal, cd vào **repo root** rồi chạy:
```powershell
cd "D:\active-projects\Auto Blog Shopify NEW Rosie\Shopify Blog Automation - Github Actions"
.\scripts\run_local_executor.ps1 -Mode review
```

Nếu bạn đang ở trong thư mục Agent:
```powershell
cd ".."
.\scripts\run_local_executor.ps1 -Mode review
```

---

Sau khi sửa, commit và push lại; workflow Shopify Blog Executor và auto-fix-sequential sẽ chạy được.
