#!/usr/bin/env bash
set -euo pipefail

# One-shot setup for a dedicated Ubuntu self-hosted runner used by ChatGPT UI automation.
# Required permissions: sudo on the VM and repo admin rights for runner registration.

REPO="${REPO:-rozy0311/Shopify-Blog-Automation---Github-Actions}"
REPO_DIR="${REPO_DIR:-$HOME/Shopify-Blog-Automation---Github-Actions}"
RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner-chatgpt-ui}"
RUNNER_NAME="${RUNNER_NAME:-$(hostname)-chatgpt-ui}"
RUNNER_LABELS="${RUNNER_LABELS:-self-hosted,linux,chatgpt-ui}"
NODE_MAJOR="${NODE_MAJOR:-20}"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: GitHub CLI (gh) is required. Install and run 'gh auth login' first."
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh is not authenticated. Run: gh auth login"
  exit 1
fi

echo "[1/8] Installing base packages"
sudo apt-get update
sudo apt-get install -y curl git jq unzip ca-certificates xvfb

echo "[2/8] Installing Node.js ${NODE_MAJOR}.x"
curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | sudo -E bash -
sudo apt-get install -y nodejs
node -v
npm -v

echo "[3/8] Preparing repository at ${REPO_DIR}"
if [ ! -d "$REPO_DIR/.git" ]; then
  git clone "https://github.com/${REPO}.git" "$REPO_DIR"
fi

cd "$REPO_DIR"
npm ci
npx playwright install --with-deps chromium

echo "[4/8] Fetching latest GitHub Actions runner version"
runner_version="$(gh api repos/actions/runner/releases/latest --jq '.tag_name' | sed 's/^v//')"
if [ -z "$runner_version" ]; then
  echo "ERROR: Could not resolve runner version"
  exit 1
fi

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

echo "[5/8] Downloading runner v${runner_version}"
runner_tgz="actions-runner-linux-x64-${runner_version}.tar.gz"
if [ ! -f "$runner_tgz" ]; then
  curl -fL -o "$runner_tgz" "https://github.com/actions/runner/releases/download/v${runner_version}/${runner_tgz}"
fi

tar xzf "$runner_tgz"

echo "[6/8] Creating registration token"
registration_token="$(gh api -X POST "repos/${REPO}/actions/runners/registration-token" --jq '.token')"
if [ -z "$registration_token" ]; then
  echo "ERROR: Failed to get runner registration token"
  exit 1
fi

echo "[7/8] Configuring runner"
./config.sh --unattended \
  --url "https://github.com/${REPO}" \
  --token "$registration_token" \
  --name "$RUNNER_NAME" \
  --labels "$RUNNER_LABELS" \
  --work "_work" \
  --replace

echo "[8/8] Installing runner service"
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status || true

cat <<EOF

Setup complete.

Next steps:
1) On the runner machine, bootstrap ChatGPT login:
   cd "$REPO_DIR"
   node ui-automation/scripts/chatgpt_persistent_bootstrap.mjs

2) Upload the generated storage-state secret:
   gh secret set CHATGPT_UI_STORAGE_STATE_B64 --repo "$REPO" < "$REPO_DIR/.chatgpt-storageState.json.b64.txt"

3) Set repo variables using the helper script from your local machine:
   scripts/set_chatgpt_ui_repo_config.ps1

EOF
