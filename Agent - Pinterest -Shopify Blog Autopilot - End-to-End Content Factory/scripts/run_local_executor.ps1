# Wrapper: chạy local executor từ repo root (Shopify Blog Automation - Github Actions).
# Script thật nằm ở repo root: scripts/run_local_executor.ps1
# Cách chạy từ thư mục Agent: .\scripts\run_local_executor.ps1 -Mode review

param(
  [ValidateSet("review", "publish")]
  [string]$Mode = "review"
)

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$mainScript = Join-Path $repoRoot "scripts\run_local_executor.ps1"

if (-not (Test-Path $mainScript)) {
  Write-Error "Không tìm thấy script tại repo root. Repo root: $repoRoot"
  Write-Host "Đảm bảo bạn đang trong repo 'Shopify Blog Automation - Github Actions' (thư mục Agent nằm bên trong)."
  Write-Host "Hoặc chạy trực tiếp từ repo root: .\scripts\run_local_executor.ps1 -Mode $Mode"
  exit 1
}

& $mainScript -Mode $Mode
