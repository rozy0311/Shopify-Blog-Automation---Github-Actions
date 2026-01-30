#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-review}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f ".env" ]; then
  while IFS= read -r line; do
    line="$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [ -z "$line" ] && continue
    [[ "$line" =~ ^# ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    key="$(echo "$key" | xargs)"
    value="$(echo "$value" | xargs | sed -e 's/^"//' -e 's/"$//')"
    [ -n "$key" ] && export "$key=$value"
  done < ".env"
fi

export MODE="$MODE"
if [ -z "${LOCAL_ONLY:-}" ]; then
  export LOCAL_ONLY="true"
fi

if [ -z "${LOCAL_HEARTBEAT_FILE:-}" ]; then
  export LOCAL_HEARTBEAT_FILE="local_heartbeat.json"
fi
timestamp="$(date +%s)"
iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
printf '{"timestamp":%s,"iso":"%s"}\n' "$timestamp" "$iso" > "$LOCAL_HEARTBEAT_FILE"

if [ "${LOCAL_HEARTBEAT_PUSH:-false}" = "true" ]; then
  git add "$LOCAL_HEARTBEAT_FILE" >/dev/null
  git commit -m "Update local heartbeat" >/dev/null || true
  git push >/dev/null || true
fi

if [ -z "${CONFIG_FILE:-}" ] && [ -z "${LLM_CONTROL_PROMPT:-}" ]; then
  echo "WARNING: Set CONFIG_FILE or LLM_CONTROL_PROMPT in .env before running."
fi

if [ -z "${QUEUE_FILE:-}" ] && [ -z "${QUEUE_URL:-}" ] && [ -z "${SHEETS_ID:-}" ]; then
  echo "WARNING: Set QUEUE_FILE/QUEUE_URL or SHEETS_ID for input queue."
fi

npm ci
npm run --workspace apps/executor build
node apps/executor/dist/index.js
