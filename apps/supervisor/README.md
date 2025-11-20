# Supervisor (AI Ops Brain)

Runs every ~30 minutes to inspect Google Sheet queue size, recent GitHub Action runs, and guardrail flags, then decides whether to dispatch review or publish runs, disable the workflow, or escalate.

## Commands

```bash
npm ci
npm run build
npm start    # executes one supervisor tick locally
```

## Required env vars

```ini
GITHUB_TOKEN=ghp_xxx (not needed inside GitHub Actions)
GITHUB_OWNER=rozy0311   # or set GITHUB_REPOSITORY=owner/repo
GITHUB_REPO=shopify-blog-automation
SLACK_WEBHOOK=... (optional)
SHEETS_ID=...
SHEETS_RANGE=Sheet1!A:B
CONFIG_RANGE=CONFIG!A:B
WF_ENABLED=false
ALLOW_PUBLISH=human_disabled
```

For Google Sheets access, either:

- run from an environment where `GOOGLE_APPLICATION_CREDENTIALS` points to a service-account JSON that has access to the sheet, or
- provide user credentials via `gcloud auth application-default login`.

The supervisor never sets `ALLOW_PUBLISH=human_enabled`; humans own that flag.
