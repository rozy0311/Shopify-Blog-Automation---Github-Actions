# Self-Hosted Cloud Runner Checklist for ChatGPT UI (ViralOps-style)

This runbook configures direct ChatGPT UI automation on a dedicated self-hosted runner so workflow runs behave consistently and do not depend on a local laptop.

## Target outcome

1. Workflow `publish.yml` runs on a cloud self-hosted runner.
2. Provider order stays `chatgpt_ui,gemini,github_models,openai`.
3. Strict mode stays enabled (`CHATGPT_UI_REQUIRED=true`).
4. One review run processes at least 1 item with `processed > 0`.

## Quick scripts in this repo

1. Windows runner setup script (recommended for your setup):

```powershell
scripts/setup_self_hosted_runner_windows.ps1
```

2. Ubuntu runner setup script (optional):

```bash
scripts/setup_self_hosted_runner_ubuntu.sh
```

3. Repo variable/secret setup script (run from Windows PowerShell):

```powershell
scripts/set_chatgpt_ui_repo_config.ps1
```

## 1) Provision a dedicated runner VM

1. Create a Windows Server VM (Windows Server 2022/2025), 4 vCPU, 8 GB RAM minimum.
2. Use a static outbound IP or stable NAT.
3. Keep this runner dedicated to ChatGPT UI tasks only.
4. Install prerequisites:

```powershell
winget install Git.Git
winget install OpenJS.NodeJS.LTS
winget install GitHub.cli
```

5. Run one-shot setup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_self_hosted_runner_windows.ps1
```

Alternative Linux flow (if needed):

```bash
sudo apt-get update
sudo apt-get install -y curl git jq unzip ca-certificates xvfb
```

## 2) Register self-hosted runner with labels

1. In GitHub repository settings, create a self-hosted runner for this repo.
2. Add labels exactly as below:

- self-hosted
- windows
- chatgpt-ui

3. Confirm runner is online and idle.

## 3) Set repository variable for runs-on routing

Set repo variable `CHATGPT_UI_RUNNER_LABELS_JSON` to:

```json
["self-hosted","linux","chatgpt-ui"]

For Windows runner use:

```json
["self-hosted","windows","chatgpt-ui"]
```
```

You can set it with GitHub CLI:

```bash
gh variable set CHATGPT_UI_RUNNER_LABELS_JSON --repo rozy0311/Shopify-Blog-Automation---Github-Actions --body '["self-hosted","windows","chatgpt-ui"]'
```

## 4) Configure required ChatGPT UI variables

Set these repository variables:

1. `CHATGPT_UI_ENABLED=true`
2. `CHATGPT_UI_REQUIRED=true`
3. `CHATGPT_UI_MODEL_LABEL=5.4 Thinking`
4. `CHATGPT_UI_STRICT_MODEL=true`
5. `CHATGPT_UI_BASE_URL=https://chatgpt.com/`
6. `CHATGPT_UI_NODE_SCRIPT=ui-automation/scripts/chatgpt_ui.mjs`
7. `CHATGPT_UI_HEADLESS=true`
8. Keep `CHATGPT_UI_BRIDGE_URL` empty when using direct UI mode.

## 5) Bootstrap authenticated ChatGPT session on the runner

Do this directly on the self-hosted runner machine (not on GitHub-hosted runner):

1. Open a temporary desktop session (local GUI, RDP, VNC, or X11-forwarded browser).
2. In repo root, run:

```powershell
node ui-automation/scripts/chatgpt_persistent_bootstrap.mjs
```

3. Complete login and any challenge in browser.
4. Wait until script saves `.chatgpt-storageState.json` and `.chatgpt-storageState.json.b64.txt`.

## 6) Upload storage state as repository secret

1. Copy content of `.chatgpt-storageState.json.b64.txt`.
2. Set GitHub secret `CHATGPT_UI_STORAGE_STATE_B64`.

Example via CLI:

```powershell
Get-Content .chatgpt-storageState.json.b64.txt -Raw | gh secret set CHATGPT_UI_STORAGE_STATE_B64 --repo rozy0311/Shopify-Blog-Automation---Github-Actions
```

## 7) Smoke test end-to-end

Trigger one review item:

```bash
gh workflow run publish.yml \
  --repo rozy0311/Shopify-Blog-Automation---Github-Actions \
  --ref feat/openai-first-gemini-fallback-chain \
  -f mode=review -f start_at=1 -f max_items=1 -f reason='self-hosted smoke test'
```

Pass criteria:

1. Job lands on self-hosted runner labels.
2. No preflight error about dedicated self-hosted runner.
3. No `Not authenticated (no chat textbox)` error.
4. Summary shows `processed >= 1` and no strict ChatGPT UI crash.

## 8) Operating checklist (daily)

1. Runner online and idle before schedule window.
2. `CHATGPT_UI_STORAGE_STATE_B64` age less than 7 days.
3. Last run artifact has no `out/chatgpt-ui-debug` auth error report.
4. If title becomes `Just a moment...`, refresh login state (repeat step 6 and 7).

## 9) Recovery playbook

1. If preflight fails with dedicated runner error:
- Re-check `CHATGPT_UI_RUNNER_LABELS_JSON` value and runner labels.

2. If runtime fails with `Not authenticated` and `Just a moment...`:
- Re-bootstrap login on the same self-hosted runner.
- Re-upload fresh `CHATGPT_UI_STORAGE_STATE_B64`.

3. If cloud IP gets repeatedly challenged:
- Move to bridge mode (`CHATGPT_UI_BRIDGE_URL`) from a trusted browser environment.
- Keep strict mode enabled so fallback does not hide auth failures.

## 10) Security guardrails

1. Never commit storage state files.
2. Rotate ChatGPT session state periodically.
3. Restrict runner repository access to this project only.
4. Keep branch protection and PR-only workflow unchanged.
