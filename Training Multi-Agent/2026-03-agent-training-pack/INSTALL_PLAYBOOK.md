# Install Playbook

## 0) Prerequisites
- Python 3.10+
- VS Code + terminal PowerShell
- API key đặt trong `.env` (không hardcode)

## 1) Tạo virtual env
```powershell
cd "D:\active-projects\Sơ đồ Multi-Agent Enterprise AI system hoàn chỉnh và production-ready ( Reconcilegpt)\Training Multi-Agent\2026-03-agent-training-pack"
New-Item -ItemType Directory -Force "D:\.venvs" | Out-Null
python -m venv "D:\.venvs\agent-training-pack"
& "D:\.venvs\agent-training-pack\Scripts\Activate.ps1"
```

> Vì path workspace rất dài, dùng venv path ngắn để tránh lỗi `WinError 206` khi cài package lớn như `numpy`.

## 2) Cài package nền
```powershell
pip install --upgrade pip
pip install pydantic python-dotenv rich
pip install openai langgraph streamlit
```

## 3) Chuẩn bị secrets
Tạo file `.env`:
```env
OPENAI_API_KEY=YOUR_KEY
OPENAI_MODEL=gpt-4.1-mini
MEMORY_OBSERVER_THRESHOLD=30000
MEMORY_REFLECTOR_THRESHOLD=40000
```

## 4) Test memory cycle local
```powershell
python .\scripts\run_memory_cycle.py
```
Kỳ vọng: xuất observation log + bản reflect hợp nhất.

## 5) Áp dụng prompt template
- Dùng `templates/system_prompt_memory_hitl.md` làm system prompt cho orchestrator.
- Dùng `templates/observation_schema.json` để validate memory cell.
- Dùng `templates/webmcp_tool_contract.json` làm mẫu contract tool.

## 6) Vận hành an toàn
- Mặc định `execute=false` cho task chưa được approve.
- Chỉ bật execution khi có human sign-off.
- Không cấp quyền filesystem/network rộng trừ khi bắt buộc.
