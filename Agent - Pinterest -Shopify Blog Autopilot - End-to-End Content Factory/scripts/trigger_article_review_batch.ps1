# Trigger Article Pre-Publish Review cho nhiều bài (đọc ID từ file hoặc tham số).
# Dùng: .\trigger_article_review_batch.ps1 -Ids 691791954238,691731595582
#   hoặc: .\trigger_article_review_batch.ps1 -FromFile article_ids_to_fix.txt
# Chạy từ repo root (parent của "Agent - Pinterest...Content Factory") hoặc từ thư mục chứa .github.

param(
    [string[]] $Ids = @(),
    [string]   $FromFile = "",
    [int]      $DelaySeconds = 30,
    [string]   $Ref = "feat/l6-reconcile-main"
)

$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
if ($repoRoot -match "Agent - Pinterest.*Content Factory\\scripts") {
    $repoRoot = (Get-Item $repoRoot).Parent.Parent.FullName
}
Set-Location $repoRoot

$allIds = @()
if ($FromFile) {
    $path = $FromFile
    if (-not [System.IO.Path]::IsPathRooted($path)) {
        $path = Join-Path $PSScriptRoot $path
    }
    if (-not (Test-Path $path)) {
        Write-Error "File not found: $path"
    }
    $allIds = Get-Content $path -Raw | ForEach-Object { $_ -split "[\r\n,;\s]+" } | Where-Object { $_ -match "^\d+$" }
}
if ($Ids.Count -gt 0) {
    $allIds = @($allIds) + @($Ids)
}

if ($allIds.Count -eq 0) {
    Write-Host "No article IDs. Use -Ids 123,456 or -FromFile path/to/ids.txt"
    exit 0
}

$total = $allIds.Count
Write-Host "Triggering Article Pre-Publish Review for $total article(s). Delay between triggers: ${DelaySeconds}s"
$n = 0
foreach ($id in $allIds) {
    $n++
    Write-Host "[$n/$total] article_id=$id"
    gh workflow run "Article Pre-Publish Review" --ref $Ref -f "article_id=$id"
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "gh workflow run failed for $id"
    }
    if ($n -lt $total -and $DelaySeconds -gt 0) {
        Start-Sleep -Seconds $DelaySeconds
    }
}
Write-Host "Done. Check runs: gh run list --workflow=`"Article Pre-Publish Review`" -L $total"
