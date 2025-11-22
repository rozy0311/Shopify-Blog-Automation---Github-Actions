# Shopify Blog Automation

Content pipeline + supervisor to turn Google Sheet queues into Shopify blog posts with Level-6 guardrails. The repo is split into two deployable apps:

| Path | Role |
| --- | --- |
| `apps/executor/` | Node/TypeScript pipeline that reads Google Sheets, calls OpenAI (JSON mode), posts to Shopify, backfills the sheet, writes previews/artifacts, and can run via cron (GitHub Actions or local autorun). |
| `apps/supervisor/` | AI Ops brain that inspects queue health + recent workflow runs, flips safety flags, dispatches review/publish runs, and notifies humans via Slack. |

## Quick Start

```bash
# Install workspace deps
npm install --workspaces

# Build executor & supervisor
npm run --workspace apps/executor build
npm run --workspace apps/supervisor build
```

See each app's README for configuration, env vars, and runbooks.

> 🔐 Google Sheets auth: for local runs, set `GOOGLE_SERVICE_ACCOUNT_JSON` (or `GOOGLE_APPLICATION_CREDENTIALS_JSON`) to the full service-account JSON string. In CI we inject the same secret and also export `GOOGLE_APPLICATION_CREDENTIALS` so Application Default Credentials keep working.

## GitHub Actions workflows

- `.github/workflows/publish.yml` – runs the executor on schedule (13:05/19:05/02:05 UTC) and via manual dispatch, uploads previews + summary artifacts, respects `WF_ENABLED`, and supports review/publish modes.
- Workflow runs are now named `Shopify Blog Executor (review)` or `(... publish)` so the supervisor can reason about recent history at a glance.
- `.github/workflows/supervisor.yml` – runs every 30 minutes to evaluate queue health, recent runs, and guardrail flags. It can trigger review-only runs, raise incidents, or request publishes when safe.

## Required secrets & variables (GitHub Actions)

| Type | Key | Purpose |
| --- | --- | --- |
| Variable | `SHEETS_ID` | Google Sheet ID containing CONFIG + queue tabs |
| Variable | `SHEETS_RANGE` | e.g. `Sheet1!A:B` |
| Variable | `CONFIG_RANGE` | e.g. `CONFIG!A:B` |
| Variable | `SHOPIFY_SHOP` | Shopify shop subdomain |
| Variable | `BLOG_HANDLE` | Target blog handle (default `agritourism`) |
| Variable | `AUTHOR` | Shopify article author (default `The Rike`) |
| Variable | `OPENAI_MODEL` | Model name (default `gpt-4o-mini`) |
| Variable | `WF_ENABLED` | `false` by default (dry-run) |
| Variable | `ALLOW_PUBLISH` | `human_disabled` by default; supervisor never sets to `human_enabled` |
| Secret | `SHOPIFY_ACCESS_TOKEN` | Admin API token with `write_content` (workflow exposes it as `SHOPIFY_TOKEN`) |
| Secret | `OPENAI_API_KEY` | OpenAI API key |
| Secret | `GOOGLE_SERVICE_ACCOUNT_JSON` | Full Google service-account JSON string; both apps read it directly and workflows also export it to `GOOGLE_APPLICATION_CREDENTIALS` for ADC |
| Secret | `SLACK_WEBHOOK` | (Optional) incoming webhook for supervisor notifications |

> ℹ️ **Supervisor / GitHub variables** – When the supervisor runs with the default `GITHUB_TOKEN`, GitHub may block API calls that read/write repository variables during scheduled runs. In that case the job now keeps going, logs a warning, and pings you to flip `WF_ENABLED` / `ALLOW_PUBLISH` manually. If you need the agent to auto-toggle those variables, provide it a fine-grained PAT (e.g. via a new secret and env) with `Actions:read/write` scope and update the workflow to use that token.

## Review-first workflow

1. Run executor in `review` mode (default) locally or via `workflow_dispatch`.
2. Inspect HTML/JSON drafts under `apps/executor/out/review` or the uploaded GitHub artifact / Pages preview.
3. Flip `WF_ENABLED=true` *and* `ALLOW_PUBLISH=human_enabled` when you're ready.
4. Supervisor will only dispatch publish once the latest review succeeded and risk thresholds are satisfied.

## Tracing

- OpenTelemetry tracing is enabled by default and exports spans to `http://localhost:4318/v1/traces`. Override via `OTEL_EXPORTER_OTLP_ENDPOINT` or disable with `ENABLE_TRACING=false`.
- Each app announces a `service.name` (`shopify-blog-executor` / `shopify-blog-supervisor`). Override via `TRACING_SERVICE_NAME` if you need custom labels.
- Before running locally, launch the AI Toolkit tracing collector/viewer via the command palette action **AI Toolkit: Open Tracing** (`ai-mlstudio.tracing.open`) so spans have a listener.
