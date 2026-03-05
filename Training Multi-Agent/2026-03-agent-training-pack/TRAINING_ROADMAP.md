# Training Roadmap (4 Weeks)

## Week 1 — Stabilize Memory + Safety
- [ ] Bật observational memory loop (Observer/Reflector).
- [ ] Chuẩn hóa schema observation + salience.
- [ ] Thiết lập approval gate cho mọi tool có side-effect.
- [ ] Viết 20 test prompts cho tình huống quên ngữ cảnh.

**Deliverable:** Agent giữ context ổn định qua >= 30 lượt hội thoại.

## Week 2 — Skill Contracts + Tool Reliability
- [ ] Chuyển skill calls sang contract JSON schema.
- [ ] Thêm preflight validation cho tool args.
- [ ] Thêm post-execution audit log (tool, args_hash, result_summary).
- [ ] Gắn risk label cho từng skill: low/medium/high.

**Deliverable:** Skill execution có trace đầy đủ và rollback-safe.

## Week 3 — HITL UX and Orchestration Quality
- [ ] Áp dụng Plan→Approve→Execute cho luồng chính.
- [ ] Thêm màn hình review plan (edit JSON trước execute).
- [ ] Thiết kế conflict resolution node (ReconcileGPT).
- [ ] Thêm timeout/fallback khi reviewer không phản hồi.

**Deliverable:** Luồng có người duyệt vận hành ổn cho task rủi ro trung/cao.

## Week 4 — Evaluation + Cost Discipline
- [ ] Đo: memory recall rate, hallucination rate, token/session.
- [ ] So sánh: dynamic RAG vs observational memory trên cùng tập test.
- [ ] Tối ưu chunk size Observer/Reflector theo chi phí thực tế.
- [ ] Chốt baseline cấu hình cho production-like staging.

**Deliverable:** Báo cáo KPI + config baseline để rollout.

---

## KPI đề xuất
- `memory_recall_rate >= 0.85`
- `approval_bypass_incidents = 0`
- `critical_tool_error_rate < 1%`
- `token_cost_per_session giảm >= 25% so với baseline`
