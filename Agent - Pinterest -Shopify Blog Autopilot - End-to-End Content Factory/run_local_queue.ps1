# Local queue runner with heartbeat - Shopify Blog Autopilot
# Usage: .\run_local_queue.ps1 [-MaxItems 5] [-DelaySeconds 600]

param(
  [int]$MaxItems = 5,
  [int]$DelaySeconds = 600
)

$ErrorActionPreference = "Stop"
$scriptRoot = $PSScriptRoot
$repoRoot = Split-Path -Parent $scriptRoot
$pipelineDir = Join-Path $scriptRoot "pipeline_v2"
$heartbeatPath = Join-Path $repoRoot "local_heartbeat.json"
$envPath = Join-Path $scriptRoot ".env"

if (Test-Path $envPath) {
  Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) { return }
    $parts = $line.Split("=", 2)
    if ($parts.Length -eq 2) {
      $name = $parts[0].Trim()
      $value = $parts[1].Trim().Trim('"').Trim("'")
      if ($name) { [System.Environment]::SetEnvironmentVariable($name, $value, "Process") }
    }
  }
}

$env:LOCAL_ONLY = "true"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$logDir = Join-Path $scriptRoot "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

function Update-Heartbeat {
  $payload = @{ timestamp = [int][DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); iso = (Get-Date).ToUniversalTime().ToString("o") }
  $payload | ConvertTo-Json -Depth 3 | Set-Content -Path $heartbeatPath -Encoding UTF8
  # Optional: push heartbeat to repo so GHA can skip when local is running
  if ($env:LOCAL_HEARTBEAT_PUSH -eq "true" -and (Test-Path (Join-Path $repoRoot ".git"))) {
    try {
      Push-Location $repoRoot
      git add local_heartbeat.json 2>$null
      git commit -m "chore: heartbeat $(Get-Date -Format 'yyyyMMdd-HHmm')" 2>$null
      git push origin HEAD 2>$null
    } catch { }
    finally { Pop-Location }
  }
}

$runArgs = @("ai_orchestrator.py", "queue-run")
if ($MaxItems -gt 0) { $runArgs += $MaxItems }
$runArgs += "--delay=$DelaySeconds"

Write-Host "Local Queue Runner - MaxItems=$MaxItems Delay=$DelaySeconds Heartbeat=$heartbeatPath" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray

$iter = 1
while ($true) {
  Write-Host "`n--- Iteration $iter ---" -ForegroundColor Yellow
  Update-Heartbeat
  $logFile = Join-Path $logDir ("queue-run_" + (Get-Date).ToString("yyyyMMdd_HHmmss") + "_iter$iter.log")
  Push-Location $pipelineDir
  try {
    python @runArgs 2>&1 | Tee-Object -FilePath $logFile
  } finally { Pop-Location }
  Write-Host "Waiting $DelaySeconds seconds..." -ForegroundColor Gray
  Start-Sleep -Seconds $DelaySeconds
  $iter++
}
