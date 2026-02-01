# Wrapper: chạy local executor từ repo root.
# File thật nằm ở: repo_root/scripts/run_local_executor.ps1
# Repo root = thư mục cha của thư mục "Agent - Pinterest -Shopify Blog Autopilot - End-to-End Content Factory"

param(
  [ValidateSet("review", "publish")]
  [string]$Mode = "review"
)

$AgentDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $AgentDir
if (-not (Test-Path "$RepoRoot\scripts\run_local_executor.ps1")) {
  Write-Error "Không tìm thấy scripts\run_local_executor.ps1 tại repo root: $RepoRoot"
  exit 1
}
Push-Location $RepoRoot
try {
  & "$RepoRoot\scripts\run_local_executor.ps1" -Mode $Mode
} finally {
  Pop-Location
}
