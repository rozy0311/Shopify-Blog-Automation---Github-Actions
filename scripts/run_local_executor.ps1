param(
  [ValidateSet("review", "publish")]
  [string]$Mode = "review"
)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (Test-Path ".env") {
  Get-Content ".env" | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $parts = $line.Split("=", 2)
    if ($parts.Length -eq 2) {
      $name = $parts[0].Trim()
      $value = $parts[1].Trim().Trim('"')
      if ($name) { [System.Environment]::SetEnvironmentVariable($name, $value) }
    }
  }
}

$env:MODE = $Mode
if (-not $env:LOCAL_ONLY) { $env:LOCAL_ONLY = "true" }

if (-not $env:CONFIG_FILE -and -not $env:LLM_CONTROL_PROMPT) {
  Write-Warning "Set CONFIG_FILE or LLM_CONTROL_PROMPT in .env before running."
}

if (-not $env:QUEUE_FILE -and -not $env:QUEUE_URL -and -not $env:SHEETS_ID) {
  Write-Warning "Set QUEUE_FILE/QUEUE_URL or SHEETS_ID for input queue."
}

npm ci
npm run --workspace apps/executor build
node apps/executor/dist/index.js
