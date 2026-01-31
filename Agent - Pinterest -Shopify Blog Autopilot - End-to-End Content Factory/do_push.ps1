$repo = "D:\active-projects\Auto Blog Shopify NEW Rosie\Shopify Blog Automation - Github Actions"
Set-Location $repo
$out = @()
$out += "=== git status ==="
$out += git status 2>&1 | Out-String
$out += "=== git add ==="
git add .github/workflows/auto-fix-sequential.yml .github/workflows/auto-fix-manual.yml 2>&1 | ForEach-Object { $out += $_ }
$out += "=== git status after add ==="
$out += git status 2>&1 | Out-String
$out += "=== git commit ==="
git commit -m "feat(workflows): publish-id on review pass, fix loop on fail (max 2 retries)" 2>&1 | ForEach-Object { $out += $_ }
$out += "=== git push ==="
git push origin copilot/vscode-mk1uh8fm-4tpw 2>&1 | ForEach-Object { $out += $_ }
$resultPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "push_result.txt"
$out | Set-Content -Path $resultPath -Encoding UTF8
Write-Host "Wrote $resultPath"
