# Executor (Pipeline)

Reads Google Sheets queue, calls OpenAI (JSON mode), validates NO YEARS, posts to Shopify, backfills the sheet, and writes previews + summary artifacts.

## Commands

```bash
npm ci
npm run build
npm run dry        # review mode (no publish, writes previews)
npm run publish    # publish mode (requires WF_ENABLED=true + secrets)
npm run autorun:dry
npm run autorun:publish
```

`MODE` env (or `WF_ENABLED`) controls whether Shopify POST/backfill is allowed.

## Required env vars

```ini
SHEETS_ID=...
SHEETS_RANGE=Sheet1!A:B
CONFIG_RANGE=CONFIG!A:B
SHOPIFY_SHOP=therikeus
BLOG_HANDLE=agritourism
AUTHOR=The Rike
WF_ENABLED=false
OPENAI_MODEL=gpt-4o-mini
SHOPIFY_TOKEN=...
OPENAI_API_KEY=...
```

When running in GitHub Actions, source these from repo variables/secrets. Local development can rely on `.env` (see `.env.sample`).
