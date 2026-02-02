# Kiểm tra 4 Workflow – Orchestrator + ReconcileGPT

Đối chiếu với:
- **PROMPT** (PROMPT ĐỂ GỌI AGENT... + MASTER_PROMPT): 11-section, 1800–2500 từ, 4 ảnh, source format, no generic, Review → Orchestrator → Preview → Publish.
- **ReconcileGPT (EMADS-PR)**: Orchestrator route → specialists → ReconcileGPT (decision) → Human Review (gate) → Execute → Monitor.

---

## 1. article-review.yml – **ĐẠT**

| Tiêu chí | Trạng thái |
|----------|------------|
| Manual trigger + article_id + publish_anyway | ✅ |
| Pre-publish review (meta-prompt) trước publish | ✅ Initial + after fix + after rebuild |
| Fix path: fix-ids → force-rebuild → fix images | ✅ |
| Publish chỉ khi có review pass hoặc publish_anyway | ✅ cleanup → set featured → publish_now_graphql |
| Fail job khi không pass và không publish_anyway | ✅ |
| Dynamic agent dir (repo root vs subfolder) | ✅ Set agent dir, BASE/pipeline_v2, scripts từ BASE |
| Artifact upload if-no-files-found: ignore | ✅ |

**ReconcileGPT**: Decision gate = pre_publish_review; override = publish_anyway (human decision). Execute = cleanup + set featured + publish.

---

## 2. auto-fix-sequential.yml – **CẦN ĐIỀU CHỈNH**

| Tiêu chí | Trạng thái |
|----------|------------|
| Schedule */10 + heartbeat skip | ✅ |
| Queue refresh → scan → rotate → queue-init | ✅ |
| Single flow: queue-run (meta fix → gate → review → cleanup → set featured → publish) | ✅ |
| Heartbeat check với GITHUB_TOKEN checkout | ✅ |

**Thiếu**:
- **Dynamic agent dir**: Các bước đang hardcode `Agent - Pinterest.../pipeline_v2`. Khi repo root là Content Factory (pipeline_v2 ở root), path sai → job fail.
- **Artifact path**: Nên dùng `pipeline_dir` để đồng bộ với cấu trúc repo.

**Điều chỉnh**: Thêm bước "Set agent dir" trong job auto-fix-one; dùng `steps.agent_dir.outputs.pipeline_dir` cho working-directory và artifact path.

---

## 3. auto-fix-manual.yml – **CẦN ĐIỀU CHỈNH NHỎ**

| Tiêu chí | Trạng thái |
|----------|------------|
| Dispatch, article_id (1 bài) hoặc queue | ✅ |
| Single article: fix-ids → force-rebuild → fix images → review → cleanup + set featured + publish khi pass | ✅ |
| Queue: queue-run (cùng flow với sequential) | ✅ |
| Dynamic agent dir | ✅ |

**Điều chỉnh**: Artifact path đang hardcode `Agent.../pipeline_v2/...`. Khi `dir=.` thì file nằm ở `pipeline_v2/`; nên dùng `${{ steps.agent_dir.outputs.pipeline_dir }}/...` để artifact upload đúng cả hai layout repo.

---

## 4. re-audit-dispatch.yml – **CẦN ĐIỀU CHỈNH**

| Tiêu chí | Trạng thái |
|----------|------------|
| Manual + cron 2h sáng, limit 250 | ✅ |
| quality_agent.py + meta_prompt_quality_agent.py | ✅ |

**Thiếu**:
- **Dynamic agent dir**: working-directory hardcode `Agent - Pinterest...`. Repo root = Content Factory thì path không tồn tại.
- **if-no-files-found: error**: Script audit export ra file tên có timestamp; nếu không có file (hoặc path sai) → upload fail → job fail. Nên dùng `ignore` hoặc `warn`.

**Điều chỉnh**: Thêm "Set agent dir"; working-directory = `steps.agent_dir.outputs.dir`; artifact path = `${{ steps.agent_dir.outputs.dir }}/quality_report_*.json` và tương tự; if-no-files-found: ignore.

---

## Tổng kết

- **article-review.yml**: Giữ nguyên, đã đúng PROMPT + ReconcileGPT.
- **auto-fix-sequential.yml**: Thêm Set agent dir, dùng pipeline_dir cho working-directory và artifact.
- **auto-fix-manual.yml**: Artifact path dùng pipeline_dir.
- **re-audit-dispatch.yml**: Thêm Set agent dir, working-directory và artifact theo dir; if-no-files-found: ignore.

Sau khi sửa, cả 4 workflow hoạt động đúng dù repo layout là root = Content Factory hay root = parent (có subfolder Agent...).
