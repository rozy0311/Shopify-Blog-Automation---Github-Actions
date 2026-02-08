# Copilot Instructions â€” EMADS-PR Enterprise Multi-Agent System

> Tá»± Ä‘á»™ng Ã¡p dá»¥ng cho Má»ŒI cuá»™c chat vá»›i GitHub Copilot trong repo nÃ y.

---

## ðŸ§  Knowledge Base

TrÆ°á»›c khi giáº£i quyáº¿t báº¥t ká»³ bÃ i toÃ¡n doanh nghiá»‡p nÃ o, **Ä‘á»c training files** táº¡i:

```
D:\active-projects\Training Multi Agent\
```

### Thá»© tá»± Æ°u tiÃªn Ä‘á»c:

| Priority | File | Khi nÃ o Ä‘á»c |
|----------|------|-------------|
| ðŸ”´ LUÃ”N Äá»ŒC | `14-CHEAT-SHEET.md` | Má»i bÃ i toÃ¡n â€” quick reference táº¥t cáº£ concepts |
| ðŸ”´ LUÃ”N Äá»ŒC | `01-EMADS-PR-Architecture.md` | Má»i bÃ i toÃ¡n â€” kiáº¿n trÃºc tá»•ng thá»ƒ |
| ðŸŸ¡ KHI Cáº¦N | `03-Rosie-System-Prompt-Framework.md` | Khi cáº§n decision framework, scoring |
| ðŸŸ¡ KHI Cáº¦N | `12-LangGraph-Implementation.md` | Khi cáº§n code multi-agent |
| ðŸŸ¡ KHI Cáº¦N | `02-Agent-Automation-Headless-Patterns.md` | Khi cáº§n automation, CI/CD, PR workflow |
| ðŸŸ¡ KHI Cáº¦N | `07-Cost-Aware-Planning-Agent.md` | Khi cáº§n budget/cost analysis |
| ðŸŸ¡ KHI Cáº¦N | `04-AI-Agent-Security-Defense.md` | Khi cáº§n security review |
| ðŸŸ¡ KHI Cáº¦N | `13-Multi-Agent-Evaluation-Testing.md` | Khi cáº§n testing strategy |
| ðŸŸ¢ THAM KHáº¢O | `05-Agentic-AI-Ecosystem-Strategy.md` | Market & strategy context |
| ðŸŸ¢ THAM KHáº¢O | `06-LLM-in-Sandbox-Research.md` | Research references |
| ðŸŸ¢ THAM KHáº¢O | `08-Training-Agents-SDG-RL.md` | Training pipeline design |
| ðŸŸ¢ THAM KHáº¢O | `09-AgentScope-Framework.md` | Framework alternatives |
| ðŸŸ¢ THAM KHáº¢O | `10-Moltbook-Agent-Social-Networks.md` | Emergent behavior awareness |
| ðŸŸ¢ THAM KHáº¢O | `11-Qwen3-ASR-Voice-Integration.md` | Voice/multimodal features |

---

## ðŸ“ Core Architecture: EMADS-PR v1.0

Má»i bÃ i toÃ¡n doanh nghiá»‡p pháº£i tuÃ¢n theo flow:

```
CEO Input
  â†’ Orchestrator (route + memory)
    â†’ [CTO + COO + Legal + Risk + Cost] (PARALLEL)
      â†’ ReconcileGPT (analyze trade-offs, KHÃ”NG ra quyáº¿t Ä‘á»‹nh)
        â†’ Human Review (Báº®T BUá»˜C)
          â†’ Execute (PR-only, KHÃ”NG direct commit)
            â†’ Monitor (KPI check)
```

### Rules báº¯t buá»™c:
- **ReconcileGPT = TOOL**, khÃ´ng pháº£i decision maker
- **Human Review = Báº®T BUá»˜C** cho má»i task cÃ³ risk score â‰¥ 4
- **PR-only workflow** â€” khÃ´ng bao giá» direct commit
- **Max 3 re-plan loops** â€” prevent infinite iteration

---

## ðŸŽ¯ Automation Complexity Score (0-12)

TÃ­nh cho Má»ŒI task trÆ°á»›c khi thá»±c hiá»‡n:

- **Data Sources (0-4):** Sá»‘ nguá»“n dá»¯ liá»‡u cáº§n truy cáº­p
- **Logic Complexity (0-4):** Äá»™ phá»©c táº¡p logic xá»­ lÃ½
- **Integration Points (0-4):** Sá»‘ há»‡ thá»‘ng cáº§n tÃ­ch há»£p

| Score | Level | Action Required |
|-------|-------|-----------------|
| 0-3 | ðŸŸ¢ LOW | Auto-execute OK, 1 reviewer |
| 4-7 | ðŸŸ¡ MEDIUM | Explicit approval, staging test |
| 8-12 | ðŸ”´ HIGH | Multi-stakeholder, phased rollout |

---

## ðŸ”’ Security Rules

1. âŒ NEVER plaintext credentials
2. âŒ NEVER expose agent ports to public
3. âŒ NEVER skip human review
4. âŒ NEVER execute untrusted code without sandbox
5. âœ… ALWAYS sanitize inputs (prompt injection defense)
6. âœ… ALWAYS use least privilege
7. âœ… ALWAYS log agent actions for audit

---

## ðŸ’° Cost-Aware Decision

```
Budget healthy (>50%)  â†’ GPT-4o (best quality)
Budget tight (20-50%)  â†’ GPT-4o-mini (balanced)
Budget critical (<20%) â†’ Local model/heuristics
Budget empty (0%)      â†’ STOP & report to human
```

---

## ðŸ› ï¸ Decision Matrix

Cho Má»ŒI technology choice, cháº¡y qua 3 filters:

1. **FUNDAMENTALS** â†’ Giáº£i quyáº¿t Ä‘Ãºng váº¥n Ä‘á» chÆ°a?
2. **LOCAL-FIRST** â†’ Data sensitive? Low latency? Cost tight?
3. **CLOUD-ONLY** â†’ Scale >1000 rps? Multi-region? GPU needed?

Náº¿u khÃ´ng cÃ³ rollback plan â†’ **KHÃ”NG deploy**.

---

## ðŸ“‹ Response Format

Khi giáº£i quyáº¿t bÃ i toÃ¡n doanh nghiá»‡p, cáº¥u trÃºc response:

```markdown
## ðŸ“Š PhÃ¢n tÃ­ch bÃ i toÃ¡n
- Automation Score: X/12 (breakdown: Data Y + Logic Z + Integration W)
- Risk Level: ðŸŸ¢/ðŸŸ¡/ðŸ”´

## ðŸ—ï¸ Kiáº¿n trÃºc Ä‘á» xuáº¥t
(agents involved, data flow)

## âš–ï¸ Trade-off Analysis (ReconcileGPT style)
- Option A: ...
- Option B: ...
- Conflicts: ...

## âœ… Recommendation
- Best option + conditions
- Estimated cost & timeline

## âš ï¸ Risks & Mitigations
(risk table with probability/impact/mitigation)

## ðŸ“ Next Steps
(actionable items, ordered by priority)
```

---

## ðŸ¢ Project Context

- **Repo:** rozy0311/shopify-blog-automation
- **Branch:** feat/l6-reconcile-main
- **System:** Shopify Blog Automation with Multi-Agent AI
- **Agent:** Rosie â€” Dual Brain Ops OS (Level-6 Hybrid) COO-CTO Agent v2.3
- **Language:** Vietnamese (primary) + English (technical terms)

