# Sửa lỗi workflow – áp dụng thủ công

Hai lỗi cần sửa **trong repo gốc** (Shopify Blog Automation - Github Actions, thư mục chứa `.github/workflows/`).

---

## 1. Shopify Blog Executor – Check local heartbeat (SyntaxError)

**Nguyên nhân:** Trong `publish.yml`, Python nhận chuỗi có `\n` dạng ký tự (backslash + n), không phải xuống dòng → SyntaxError.

**File:** `.github/workflows/publish.yml`  
**Bước:** "Check local heartbeat"

**Cách sửa:** Thay **hai** lệnh `python -c "..."` bằng cú pháp bash `$'...'` để `\n` được hiểu là newline.

### Thay dòng URL (khoảng dòng 125):

**Cũ:**
```yaml
            heartbeat_ts=$(python -c "import json, os, urllib.request; url=os.environ.get('LOCAL_HEARTBEAT_URL','');\ntry:\n  resp=urllib.request.urlopen(url,timeout=10)\n  data=json.loads(resp.read().decode('utf-8'))\n  print(str(data.get('timestamp','')).strip())\nexcept Exception:\n  print('', end='')\n")
```

**Mới:**
```yaml
            heartbeat_ts=$(python -c $'import json, os, urllib.request\nurl=os.environ.get("LOCAL_HEARTBEAT_URL","")\ntry:\n  resp=urllib.request.urlopen(url,timeout=10)\n  data=json.loads(resp.read().decode("utf-8"))\n  print(str(data.get("timestamp","")).strip())\nexcept Exception:\n  pass')
```

### Thay dòng file (khoảng dòng 128):

**Cũ:**
```yaml
            heartbeat_ts=$(python -c "import json, os; path=os.environ.get('LOCAL_HEARTBEAT_FILE','local_heartbeat.json');\ntry:\n  data=json.load(open(path,'r',encoding='utf-8'))\n  print(str(data.get('timestamp','')).strip())\nexcept Exception:\n  print('', end='')\n")
```

**Mới:**
```yaml
            heartbeat_ts=$(python -c $'import json, os\npath=os.environ.get("LOCAL_HEARTBEAT_FILE","local_heartbeat.json")\ntry:\n  data=json.load(open(path,"r",encoding="utf-8"))\n  print(str(data.get("timestamp","")).strip())\nexcept Exception:\n  pass')
```

---

## 2. auto-fix-sequential.yml – YAML syntax line 245

**Nguyên nhân:** Trong YAML, giá trị `name:` có nhiều dấu `:` (vd. "Run queue (same flow as local: meta fix...") nên bị hiểu nhầm. Cần bọc trong ngoặc kép.

**File:** `.github/workflows/auto-fix-sequential.yml` (khoảng dòng 245)

**Cũ:**
```yaml
            - name: Run queue (same flow as local: meta fix, gate 9/10, targeted fix, review, publish)
```

**Mới:**
```yaml
            - name: "Run queue (same flow as local: meta fix, gate 9/10, targeted fix, review, publish)"
```

---

Sau khi sửa: lưu file, commit, push. Chạy lại workflow "Shopify Blog Executor" và kiểm tra "Check local heartbeat" không còn SyntaxError.
