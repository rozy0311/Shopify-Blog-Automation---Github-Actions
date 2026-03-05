# Perplexity Thread Capture — 4edd88e7-4cae-4dc7-ae43-609539ad019c

## Capture metadata
- Captured on: 2026-03-05
- Capture method: `r.jina.ai` static mirror
- Original URL: https://www.perplexity.ai/search/4edd88e7-4cae-4dc7-ae43-609539ad019c
- Mirror URL used: https://r.jina.ai/http://www.perplexity.ai/search/4edd88e7-4cae-4dc7-ae43-609539ad019c

## Raw thread gist (normalized)
- Chủ đề chính: so sánh OpenClaw vs AgentZero, sau đó mở rộng AgentZero vs Nanobot và câu hỏi về Qodo “Second Brain”.
- Kết luận trong thread:
  - Không cần bỏ OpenClaw ngay; nên chạy song song và benchmark theo workflow thực tế.
  - AgentZero được mô tả mạnh ở sandbox/isolated execution và task automation nặng.
  - Nanobot nhẹ, dễ tùy biến, phù hợp nghiên cứu/experiment, nhưng độ sâu production thấp hơn.
  - Qodo “Second Brain” thiên về code quality/compliance và memory cho context codebase/PR, bổ trợ chứ không thay thế general agent.

## Practical takeaways applied to this training pack
1. **Parallel benchmark first**
   - Không migration cảm tính theo hype.
   - Dùng cùng test suite cho 2–3 agent framework trước khi chốt.

2. **Security-first routing**
   - Task có side-effect hoặc credentials -> route sang stack có sandbox mạnh hơn.
   - Task chat/multi-channel nhẹ -> có thể giữ stack hiện tại nếu đã ổn định.

3. **Role split by system objective**
   - General automation agent: workflow/ops.
   - Code-quality second-brain: review/compliance/rule memory.

4. **Memory governance**
   - Dùng observation log + approval gate để tránh “quên” hoặc tự ý execute.

## Link references mentioned in thread
- AgentZero: https://www.agent-zero.ai/
- Nanobot repo context: https://github.com/HKUDS/nanobot
- Qodo blog: https://www.qodo.ai/blog/from-agents-to-the-second-brain/
- Qodo agents: https://github.com/qodo-ai/agents

## Note
Nội dung capture là bản text tĩnh lấy từ mirror để thay cho trang động Perplexity, dùng cho mục tiêu audit coverage/training continuity.
