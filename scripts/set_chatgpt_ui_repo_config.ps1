param(
  [string]$Repo = "rozy0311/Shopify-Blog-Automation---Github-Actions",
  [string]$RunnerLabelsJson = '["self-hosted","linux","chatgpt-ui"]',
  [string]$StorageStateB64File = ".chatgpt-storageState.json.b64.txt",
  [switch]$SkipSecret
)

$ErrorActionPreference = "Stop"

function Set-RepoVariable {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Value
  )

  gh variable set $Name --repo $Repo --body $Value | Out-Null
  Write-Host "Set variable: $Name=$Value"
}

Write-Host "Configuring ChatGPT UI repository variables for $Repo"

Set-RepoVariable -Name "CHATGPT_UI_RUNNER_LABELS_JSON" -Value $RunnerLabelsJson
Set-RepoVariable -Name "CHATGPT_UI_ENABLED" -Value "true"
Set-RepoVariable -Name "CHATGPT_UI_REQUIRED" -Value "true"
Set-RepoVariable -Name "CHATGPT_UI_MODEL_LABEL" -Value "5.4 Thinking"
Set-RepoVariable -Name "CHATGPT_UI_STRICT_MODEL" -Value "true"
Set-RepoVariable -Name "CHATGPT_UI_BASE_URL" -Value "https://chatgpt.com/"
Set-RepoVariable -Name "CHATGPT_UI_NODE_SCRIPT" -Value "ui-automation/scripts/chatgpt_ui.mjs"
Set-RepoVariable -Name "CHATGPT_UI_HEADLESS" -Value "true"
Set-RepoVariable -Name "CHATGPT_UI_BRIDGE_URL" -Value ""

if (-not $SkipSecret) {
  if (-not (Test-Path $StorageStateB64File)) {
    throw "Storage state file not found: $StorageStateB64File"
  }

  gh secret set CHATGPT_UI_STORAGE_STATE_B64 --repo $Repo < $StorageStateB64File
  Write-Host "Set secret: CHATGPT_UI_STORAGE_STATE_B64 from $StorageStateB64File"
}

Write-Host "Done. You can trigger smoke test:"
Write-Host "gh workflow run publish.yml --repo $Repo --ref feat/openai-first-gemini-fallback-chain -f mode=review -f start_at=1 -f max_items=1 -f reason='self-hosted smoke test'"
