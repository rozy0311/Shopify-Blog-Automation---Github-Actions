#!/usr/bin/env bash
set -euo pipefail

# Register a second self-hosted runner on the same Linux machine for this repository.
# This does NOT touch existing runner installations.

TARGET_REPO="${TARGET_REPO:-rozy0311/Shopify-Blog-Automation---Github-Actions}"
RUNNER_NAME="${RUNNER_NAME:-$(hostname)-shopify-chatgpt-ui}"
RUNNER_LABELS="${RUNNER_LABELS:-self-hosted,linux,hetzner,chatgpt-ui}"
RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner-shopify-chatgpt-ui}"

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI is required"
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh not authenticated; run gh auth login"
  exit 1
fi

echo "[1/6] Resolve latest actions runner version"
runner_version="$(gh api repos/actions/runner/releases/latest --jq '.tag_name' | sed 's/^v//')"
if [[ -z "$runner_version" ]]; then
  echo "ERROR: could not resolve runner version"
  exit 1
fi

mkdir -p "$RUNNER_DIR"
cd "$RUNNER_DIR"

runner_tgz="actions-runner-linux-x64-${runner_version}.tar.gz"
if [[ ! -f "$runner_tgz" ]]; then
  echo "[2/6] Download runner $runner_tgz"
  curl -fL -o "$runner_tgz" "https://github.com/actions/runner/releases/download/v${runner_version}/${runner_tgz}"
fi

if [[ ! -f "config.sh" ]]; then
  echo "[3/6] Extract runner"
  tar xzf "$runner_tgz"
fi

echo "[4/6] Create registration token for $TARGET_REPO"
registration_token="$(gh api -X POST "repos/${TARGET_REPO}/actions/runners/registration-token" --jq '.token')"
if [[ -z "$registration_token" ]]; then
  echo "ERROR: failed to get registration token"
  exit 1
fi

echo "[5/6] Configure new runner instance"
./config.sh --unattended \
  --url "https://github.com/${TARGET_REPO}" \
  --token "$registration_token" \
  --name "$RUNNER_NAME" \
  --labels "$RUNNER_LABELS" \
  --work "_work" \
  --replace

echo "[6/6] Install and start service"
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status || true

echo "Secondary runner registration completed for ${TARGET_REPO}."
