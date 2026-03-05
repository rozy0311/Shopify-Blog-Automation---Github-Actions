# Source Digest (Link Ingestion)

## Coverage Checklist (URL-level)

### ✅ Done (đọc được nội dung chính và trích xuất kỹ thuật)
- https://www.marktechpost.com/2026/02/14/how-to-build-a-self-organizing-agent-memory-system-for-long-term-ai-reasoning/
- https://venturebeat.com/data/observational-memory-cuts-ai-agent-costs-10x-and-outscores-rag-on-long
- https://developer.chrome.com/blog/webmcp-epp
- https://www.marktechpost.com/2026/02/14/google-ai-introduces-the-webmcp-to-enable-direct-and-structured-website-interactions-for-new-ai-agents/
- https://www.marktechpost.com/2026/02/16/how-to-build-human-in-the-loop-plan-and-execute-ai-agents-with-explicit-user-approval-using-langgraph-and-streamlit/
- https://www.marktechpost.com/2026/02/15/moonshot-ai-launches-kimi-claw-native-openclaw-on-kimi-com-with-5000-community-skills-and-40gb-cloud-storage-now/
- https://www.marktechpost.com/2026/02/07/google-ai-introduces-paperbanana-an-agentic-framework-that-automates-publication-ready-methodology-diagrams-and-statistical-plots/
- https://venturebeat.com/orchestration/mits-new-fine-tuning-method-lets-llms-learn-new-skills-without-losing-old
- https://www.marktechpost.com/2026/02/15/meet-kani-tts-2-a-400m-param-open-source-text-to-speech-model-that-runs-in-3gb-vram-with-voice-cloning-support/
- https://linas.substack.com/p/firstonepersonunicorn
- https://www.theatlantic.com/technology/2026/02/post-chatbot-claude-code-ai-agents/686029/

### ✅ Done via static capture
- https://www.perplexity.ai/search/4edd88e7-4cae-4dc7-ae43-609539ad019c
  - Trạng thái: đã ingest qua static mirror.
  - Artifact: `PERPLEXITY_THREAD_4edd88e7_CAPTURE.md`.

### 📝 Ghi chú không bỏ sót
- Các link đã có nội dung text khả dụng đều đã ingest.
- Các nguồn có tính chất dynamic/paywall/video/social có thể thiếu transcript đầy đủ nếu không có bản export.
- Khi có thêm transcript/notes từ các link social/video, append vào mục `Appendix` để giữ tính toàn vẹn dữ liệu training.

## Điểm kỹ thuật cốt lõi để áp dụng

### 1) Memory architecture
- Dùng 2 lớp:
  - **Raw recent history** (ngắn hạn, đầy đủ).
  - **Observation log** (dài hạn, đã nén, có timestamp/salience).
- Tác vụ nền:
  - **Observer**: nén chunk mới thành observation.
  - **Reflector**: hợp nhất quan sát trùng lặp, giữ decision log rõ ràng.
- Lợi ích:
  - Context prefix ổn định => cache hit cao => giảm chi phí token.
  - Dễ debug hơn vector retrieval động cho use-case hội thoại dài.

### 2) HITL boundary
- Flow chuẩn: `Plan -> Interrupt -> Human approve/edit -> Execute`.
- Chặn tool execution nếu chưa có `approved=true`.
- Mọi tác vụ có ghi dữ liệu/chi phí thật phải đi qua approval gate.

### 3) Web tooling via WebMCP mindset
- Ưu tiên tool schema rõ ràng thay vì UI scraping.
- Tách 2 mức tích hợp:
  - Declarative cho form đơn giản.
  - Imperative cho workflow nhiều bước.
- Bảo toàn quyền user bằng permission prompts và context clear.

### 4) Skill ecosystem
- Chuẩn hóa skill theo contract (name, args schema, safety level, side effects).
- Tạo registry nội bộ trước khi mở rộng sang marketplace công khai.
- Mỗi skill phải có risk class + rollback notes.

### 5) Continual learning
- Nếu fine-tune model/domain mới, ưu tiên cách tránh quên kiến thức cũ.
- Tư duy SDFT: teacher-student tự chấm trong vòng lặp có kiểm soát.
- Thực tiễn ngắn hạn: bắt đầu từ memory+prompt improvements; chỉ fine-tune khi dataset đủ sạch.

## Nguồn không parse đầy đủ / cần xác minh thủ công
- Một số URL dạng video/social/paywall có thể thiếu transcript đầy đủ.
- Với riêng Perplexity thread đã có bản capture tĩnh nội bộ để phục vụ audit/training.

## Appendix (thêm khi có nguồn bổ sung)
- Dán transcript YouTube/TikTok/ProductHunt hoặc thread export để tiếp tục ingest.
- Mỗi nguồn mới thêm theo format:
  - `URL:`
  - `Status: Done|Partial|Blocked`
  - `Key takeaways:`
  - `Applied to:` (memory/orchestration/HITL/security/cost)
