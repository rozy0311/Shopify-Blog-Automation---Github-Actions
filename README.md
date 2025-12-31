# Shopify Blog Automation

Content pipeline + supervisor to turn Google Sheet queues into Shopify blog posts with Level-6 guardrails. The repo is split into three deployable apps:

| Path | Role |
| --- | --- |
| `apps/executor/` | Node/TypeScript pipeline that reads Google Sheets, calls OpenAI (JSON mode), posts to Shopify, backfills the sheet, writes previews/artifacts, and can run via cron (GitHub Actions or local autorun). |
| `apps/supervisor/` | AI Ops brain that inspects queue health + recent workflow runs, flips safety flags, dispatches review/publish runs, and notifies humans via Slack. |
| `apps/amp/` | Command-line interface (CLI) that provides easy access to the automation tools. |

## Quick Start

### Option 1: Install via AMP CLI (Recommended)

```bash
curl -fsSL https://ampcode.com/install.sh | bash
amp
```

The installer will:
- Clone the repository
- Install all dependencies
- Build the AMP CLI
- Add `amp` command to your PATH

### Option 2: Manual Installation

```bash
# Install workspace deps
npm install --workspaces

# Build all apps
npm run --workspace apps/executor build
npm run --workspace apps/supervisor build
npm run --workspace apps/amp build
```

## Using the AMP CLI

After installation, the `amp` command provides a convenient interface:

```bash
# Check status of all components
amp status

# Build all components
amp build

# Build specific component
amp build --workspace executor

# Run executor in review mode (dry-run, no publishing)
amp run

# Run executor in publish mode
amp run --mode publish

# Run supervisor
amp supervise

# Show required environment variables
amp help-env

# Get help
amp --help
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

## No-LLM importer (index → Shopify)

`importer.mjs` lets you publish up to 30 prewritten posts without touching OpenAI. Provide either `INDEX_FILE` (local `.txt` or `.html` with one link per line / `<a>` tags) **or** `INDEX_URL` (public page that lists the links). Each source page is cleaned, checked for `NO YEARS`, deduped via `src:<sha1(url)>`, and then created or updated on Shopify.

```powershell
# Install once at repo root
npm install

# Minimal env (PowerShell example)
$env:INDEX_FILE = 'D:\drafts\batch30.html'   # or set INDEX_URL
$env:SHOPIFY_SHOP = 'therikeus'
$env:SHOPIFY_TOKEN = '<shpat_***>'
$env:BLOG_HANDLE = 'agritourism'
$env:WF_ENABLED = 'false'          # dry-run / plan
$env:STRICT_NO_YEARS = 'true'      # skip any post mentioning 19xx/20xx

# Dry-run (plan only)
node importer.mjs --mode plan

# Publish/update once the plan looks good
$env:WF_ENABLED = 'true'
node importer.mjs --mode publish
```

### Multi-file index input

- `INDEX_FILE` accepts comma/semicolon/newline-separated paths. Example:

  ```powershell
  $env:INDEX_FILE = 'blogs/index_file01.txt,blogs/index_file02.txt,blogs/index_file03.txt'
  ```

- The importer merges all links (and inline clipboard blocks) from every listed file, dedupes them, and then obeys `START_AT`/`MAX_ITEMS` so you can push Shopify products plus blog drafts in one run.

- Order matters: sources are processed in the sequence you list them, so keep the high-priority file first when batching 30 at a time.

Key behaviors:

- Dry-run respects `WF_ENABLED=false` even if you pass `--mode publish`.
- If a source page already links to `https://<shop>.myshopify.com/blogs/<handle>/<article>`, that handle is updated in place; otherwise dedupe falls back to the hashed `src:` tag or slugified title.
- SEO metafields (`global.title_tag` / `global.description_tag`) are overwritten on every update/Create so Pages stays human-readable.
- Set `SHOPIFY_RATE_LIMIT_MS` (default 1200 ms) if you need slower sequencing to avoid Admin API throttling.
- Control year stripping via `SANITIZE_YEARS` (`strip` default, `rewrite`, or `off`), `NO_YEARS_REPLACEMENT` (used when rewriting), `SANITIZE_SCOPE` (`all` default: head + body, `body`, or `head`), and `YEAR_ALLOWED` (regex whitelist). The sanitizer now scrubs titles/meta/alt text before the `STRICT_NO_YEARS` gate, so you can keep guardrails even when sources contain badges like “2023/2024”.
- Require inline payloads when you don't want the importer to fall back to scraped HTML:
  - `REQUIRE_INLINE_FOR_PRODUCTS=true` skips any product handle that doesn't have a JSON/clipboard block directly under the URL in `INDEX_FILE`/`INDEX_URL`.
  - `ALLOW_BODY_FALLBACK=false` makes inline data mandatory for every link (blog + product). Leave it `true` to keep the legacy “scrape remote HTML” behavior.

### Importer workflow (recommended)

1. **Set guardrail vars** – keep `STRICT_NO_YEARS=true`. Start with `SANITIZE_YEARS=rewrite`, `NO_YEARS_REPLACEMENT=current`, `SANITIZE_SCOPE=all`, and leave `YEAR_ALLOWED` empty unless you have a precise pattern to whitelist (e.g. `\bISO-20\d{2}\b`).
2. **Plan run** – `WF_ENABLED=false node importer.mjs --mode plan`. Aim for ≥20 `action=create`/`update` lines; scrub or replace any links that 404 or still violate guardrails.
3. **Publish the clean subset** – flip `WF_ENABLED=true` with the same sanitizer settings and rerun with `--mode publish`. Skipped links remain untouched but don’t block the batch.
4. **Fix stubborn sources** – either swap in cleaner URLs, add a laser-focused `YEAR_ALLOWED` regex, or leave them for another batch once their content is updated.

### Inline clipboard blocks + schema

- Every URL in `INDEX_FILE` can include a clipboard payload directly under it:

  ```text
  https://therike.com/blogs/.../example-post
  TITLE: Human-facing title
  SEO_TITLE: < 60 chars
  META_DESC: < 155 chars
  [HTML]
  <article>...clean body without schema...</article>
  [/HTML]
  [SCHEMA]
  <script type="application/ld+json">{...}</script>
  [/SCHEMA]
  IMAGES:
  - src: "GENERATE: ..." ; alt: ... ; slot: featured ; position: 0
  - src: https://... ; alt: ... ; slot: inline ; position: 1
  ```

- The importer now strips inline `<h2 id="schema">…</h2>` / `<script type="application/ld+json">` blocks from `[HTML]` when `STRIP_INLINE_SCHEMA=true` (default) so body_html stays clean.
- Control how schema is emitted via env vars:

  | Variable | Default | Effect |
  | --- | --- | --- |
  | `SCHEMA_MODE` | `strip` | `strip` drops schema entirely; `inline` appends the `[SCHEMA]` block back into `body_html`; `metafield` saves it to a metafield so Liquid can render `<script>` in the theme. |
  | `SCHEMA_METAFIELD_NAMESPACE` | `seo` | Namespace used when `SCHEMA_MODE=metafield`. |
  | `SCHEMA_METAFIELD_KEY` | `json_ld` | Key used when `SCHEMA_MODE=metafield`. |
  | `STRIP_INLINE_SCHEMA` | `true` | Skip removal by setting `false` if you really want schema left in body_html. |
  | `CLEAR_SCHEMA_WHEN_EMPTY` | `true` | When `SCHEMA_MODE=metafield`, remove the metafield if a URL no longer supplies `[SCHEMA]`. |

- Recommended production combo (keeps HTML clean and lets the theme render JSON-LD near `</head>`):

  ```powershell
  $env:SCHEMA_MODE = 'metafield'
  $env:SCHEMA_METAFIELD_NAMESPACE = 'seo'
  $env:SCHEMA_METAFIELD_KEY = 'json_ld'
  $env:STRIP_INLINE_SCHEMA = 'true'
  $env:CLEAR_SCHEMA_WHEN_EMPTY = 'true'
  ```

- For inline scripts (legacy themes), flip `SCHEMA_MODE=inline` and optionally `STRIP_INLINE_SCHEMA=false` so the importer leaves your `<script>` block in `body_html`.

### One-button batches for all three index files

1. Point the importer at every curated list:

  ```powershell
  $env:INDEX_FILE = 'blogs/index_file01.txt,blogs/index_file02.txt,blogs/index_file03.txt'
  $env:TARGET = 'auto'
  $env:STRICT_NO_YEARS = 'true'
  $env:SANITIZE_YEARS = 'rewrite'
  $env:SANITIZE_SCOPE = 'all'
  $env:SCHEMA_MODE = 'metafield'
  $env:STRIP_INLINE_SCHEMA = 'true'
  ```

1. Pick a batch window: `START_AT=1` / `MAX_ITEMS=30` for the first wave, then `START_AT=31`, `61`, … until all links across the three files are done. The importer dedupes across files, so you can safely leave URLs in place between runs.

1. Run plan mode once per window:

  ```powershell
  $env:WF_ENABLED = 'false'
  node importer.mjs --mode plan
  ```

  ✅ Expect each log line to show `source=inline` so you know the clipboard payload—not the live Shopify page—is being used.

1. Publish the exact same window:

  ```powershell
  $env:WF_ENABLED = 'true'
  node importer.mjs --mode publish
  ```

  Shopify updates will include `body_html`, SEO metafields, featured/inline images, and (when configured) the JSON-LD metafield for every URL in that slice.

1. Rinse and repeat for the next `START_AT` value. If one entry fails the GEO/strict-no-years gate, fix its block in-place and rerun plan/publish for that batch—everything else stays idempotent.

> Tip: keep `REQUIRE_INLINE_FOR_PRODUCTS=true` and `ALLOW_BODY_FALLBACK=false` when you only want the importer to trust the `[HTML]/[SCHEMA]/IMAGES` payload you authored in the index files.

### Non-interactive batch runners

When you are ready to let the importer chew through every curated list without pausing for confirmations, use one of the automation helpers below. Both assume you already configured Shopify + guardrail env vars and that you understand these runs will publish exactly what the index files contain.

#### PowerShell runner (`scripts/publish_all.ps1`)

- Disable VS Code prompts via `terminal.integrated.confirmOnExit=false` and run commands inside the integrated terminal (avoid Code Runner popups).
- Set your execution policy once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force`. Each run can then bypass prompts with `pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File .\scripts\publish_all.ps1 -IndexFile "blogs\index_file05.txt" -BatchSize 30 -StartAt 1`.
- Required env vars before launching: `SHOPIFY_SHOP`, `SHOPIFY_TOKEN`, `BLOG_HANDLE`, `WF_ENABLED` (script toggles it), `STRICT_NO_YEARS`, `SANITIZE_SCOPE`, `SANITIZE_YEARS`, `TARGET`. The script forces `NO_INTERACTIVE=1`, counts links, then loops windows of `START_AT`/`MAX_ITEMS`, logging plan + publish output under `out/runs/<timestamp>`.

#### Node supervisor (`autorun_publish_all.mjs`)

- Works cross-platform and iterates over `blogs/index_file01.txt`‒`index_file03.txt` by default. Override via `INDEX_FILES="blogs/index_file05.txt"`.
- Honors `BATCH_SIZE`/`START_AT` env vars, sets `NO_INTERACTIVE=1`, and sequentially runs `node importer.mjs --mode plan` / `--mode publish` for each window. Example:

  ```bash
  INDEX_FILES="blogs/index_file05.txt" BATCH_SIZE=10 START_AT=1 \
  node autorun_publish_all.mjs
  ```

- Failures per window are logged but do not halt the overall loop, so review the terminal output or the generated logs before moving to the next batch.

> **Safety reminder**: turning off prompts means the scripts will publish whatever is currently in your index files. Double-check guardrail env vars, inline payloads, and sanitizer settings before each run.

## Perplexity generator + direct publish helpers

When you want to skip Google Sheets and spin up net-new drafts straight from Perplexity, use the new helper scripts under `scripts/perplexity/`.

### 1. Generate Structured Markdown via Perplexity

```bash
# Required once
npm install

# One-off invocation (PowerShell example)
$env:PPLX_API_KEY = "pplx-***"
node scripts/perplexity/generate_from_perplexity.mjs ^
  --topic "Wild lettuce benefits" ^
  --angle "Gardeners looking for safe pain relief" ^
  --url "https://therike.com/blogs/.../wild-lettuce" ^
  --blog-handle "agritourism-adventures-exploring-farm-based-tourism"

# Outputs under artifacts/perplexity/<slug>/
#   - article.md (front-matter + <article> body)
#   - images.json (4 curated/generate prompts)
#   - response.json (raw Perplexity payload)
```

Flags:

- `--topic` (required) – the prompt topic.
- `--angle` – optional job-to-be-done.
- `--url` – reference URL passed through the prompt.
- `--author`, `--blog-handle`, `--model`, `--out-dir`, `--system-prompt`, `--user-template` for overrides.

The script enforces `STRICT_NO_YEARS` on returned title/SEO/meta/body. It also saves the JSON-LD string + image manifest for downstream upload.

### 2. Publish generated content to Shopify (blog or product)

```bash
$env:SHOPIFY_SHOP = "therikeus"
$env:SHOPIFY_TOKEN = "shpat_***"
$env:BLOG_HANDLE = "agritourism-adventures-exploring-farm-based-tourism"

node scripts/perplexity/publish_shopify.mjs artifacts/perplexity/wild-lettuce-benefits

# For products instead of blog posts
node scripts/perplexity/publish_shopify.mjs artifacts/perplexity/<slug> --target product
```

Behavior:

- Parses `article.md` front-matter (title/SEO/meta/schema/optional slug) and HTML body. If the content is Markdown, it is rendered via `marked` before upload.
- Uploads to the configured blog (`BLOG_HANDLE`) by default, or creates/updates a product when `--target product` / `TARGET=product`.
- Updates Shopify SEO fields plus a `schema.article_jsonld` metafield (JSON) when present.
- Attaches every HTTP image listed in `images.json`. Entries that start with `GENERATE:` are skipped so you can manually replace them later.
- Enforces `STRICT_NO_YEARS` before hitting Shopify, so violations fail fast.
- You can override per-run with `--shop`, `--token`, `--blog-handle`, `--target`, or provide `author`, `tags`, `slug`, `vendor` via front matter.

> Tip: keep the generated directories under version control (or archive them inside `artifacts/`) so you can diff revisions, retry publishes, or feed them back into importer workflows later.

### 3. Batch generate + publish from a queue file

When you have dozens of prompts/URLs to refresh, run everything through `scripts/perplexity/batch_generate_publish.mjs`. It reads a queue file (defaults to `blogs/blog_url_links01.txt`), calls the generator for each entry, and optionally publishes the finished articles back-to-back.

```bash
# Example (first 5 entries from blogs/blog_url_links01.txt)
$env:PPLX_API_KEY = "pplx-***"
$env:SHOPIFY_SHOP = "therikeus"
$env:SHOPIFY_TOKEN = "shpat_***"
$env:BLOG_HANDLE = "agritourism-adventures-exploring-farm-based-tourism"

node scripts/perplexity/batch_generate_publish.mjs ^
  --input blogs/blog_url_links01.txt ^
  --start 1 ^
  --max 5 ^
  --mode both ^
  --angle "Practical herbal explainer" ^
  --target blog
```

Supported formats per line:

- Plain URL (e.g. `https://therike.com/.../wild-lettuce-extract...`) – the script derives the slug + topic title automatically.
- Pipe-delimited overrides: `Topic title | Optional angle | https://source-url | blog` (target can be `blog` or `product`).

Key flags:

- `--mode generate|publish|both` – skip publish to only draft content, or skip generation to republish existing artifacts.
- `--start` / `--max` – window into the queue (useful for batches of 10/30/etc.).
- `--out-dir` – change where artifacts land (default `artifacts/perplexity`).
- `--blog-handle`, `--author`, `--target`, `--angle`, `--model` – override defaults per run.
- `--dry-run true` – log the underlying generator/publisher commands without hitting APIs.
- `--stop-on-error true` – halt the batch on the first failure instead of continuing.

Each iteration spawns the existing generator/publisher CLI, so guardrails (STRICT_NO_YEARS, schema handling, image uploads) stay consistent. Review the console summary at the end (`Completed` vs `Failed`) before moving on to the next window.
