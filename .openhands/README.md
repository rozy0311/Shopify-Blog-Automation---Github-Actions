# 🤖 AI Agent Auto-Implementation Template
# Copy thư mục này vào bất kỳ repo mới nào

Để AI tự động implement issues trong repo này:

## Quick Setup (30 giây)

1. **Copy 2 thư mục này vào repo:**
   - `.openhands/` 
   - `.github/workflows/openhands-resolver.yml`

2. **Thêm secret vào repo:**
   - Vào repo → Settings → Secrets → Actions
   - Thêm: `LLM_API_KEY` = Claude/OpenAI API key

3. **Done!**

## Cách dùng

| Trigger | Hành động |
|---------|-----------|
| Tạo issue + label `openhands` | AI tự động fix + tạo PR |
| Comment `/fix` trên issue | AI bắt đầu implement |
| Comment `@openhands help` | AI phân tích và suggest |

## Cấu trúc thư mục

```
your-repo/
├── .openhands/
│   └── config.toml          # Cấu hình agent
└── .github/
    └── workflows/
        └── openhands-resolver.yml  # GitHub Action trigger
```
