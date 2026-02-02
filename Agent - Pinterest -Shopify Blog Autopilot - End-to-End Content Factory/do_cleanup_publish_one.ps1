# One-click: cleanup (strip generic, dedupe, featured image) then publish one article.
# Usage: .\do_cleanup_publish_one.ps1 [article_id]
# Default article_id: 690496241982
# Requires .env with SHOPIFY_SHOP, SHOPIFY_ACCESS_TOKEN, SHOPIFY_BLOG_ID (or SHOPIFY_PUBLISH_CONFIG.json + .env token).

param([string]$ArticleId = "690496241982")

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

# Load .env into process environment
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$' -and $matches[1] -notmatch '^#') {
            $key = $matches[1]
            $val = $matches[2].Trim().Trim('"').Trim("'")
            [Environment]::SetEnvironmentVariable($key, $val, "Process")
        }
    }
    Write-Host "[OK] Loaded .env"
} else {
    Write-Host "[WARN] No .env found. Set SHOPIFY_SHOP, SHOPIFY_ACCESS_TOKEN, SHOPIFY_BLOG_ID in env or .env"
}

Write-Host "Cleanup → set featured image (if missing) → publish article: $ArticleId"
python pipeline_v2/cleanup_before_publish.py $ArticleId
if ($LASTEXITCODE -ne 0) {
    Write-Host "Cleanup failed. Fix errors then run again."
    exit $LASTEXITCODE
}
python pipeline_v2/set_featured_image_if_missing.py $ArticleId
python pipeline_v2/publish_now_graphql.py $ArticleId
if ($LASTEXITCODE -ne 0) {
    Write-Host "Publish failed."
    exit $LASTEXITCODE
}
Write-Host "Done: cleanup + publish for $ArticleId"
