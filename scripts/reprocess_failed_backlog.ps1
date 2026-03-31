param(
    [string]$Repo = "rozy0311/Shopify-Blog-Automation---Github-Actions",
    [string]$Branch = "feat/openai-first-gemini-fallback-chain",
    [string]$Workflow = "publish.yml",
    [int]$StartAt = 1,
    [int]$Items = 20,
    [int]$PollSeconds = 8
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
$env:GH_PAGER = "cat"

function Wait-Run([long]$RunId) {
    while ($true) {
        $state = gh run view $RunId -R $Repo --json "status,conclusion" | ConvertFrom-Json
        if ($state.status -eq "completed") {
            return $state
        }
        Start-Sleep -Seconds $PollSeconds
    }
}

$processedTotal = 0
$failedTotal = 0
$blocked = $false

for ($i = 0; $i -lt $Items; $i++) {
    $offset = $StartAt + $i
    $reason = "reprocess-failed-offset-$offset"

    Write-Host "Dispatching item offset=$offset"
    gh workflow run $Workflow -R $Repo --ref $Branch -f mode=review -f start_at=$offset -f max_items=1 -f reason=$reason | Out-Null
    Start-Sleep -Seconds 4

    $run = (gh run list -R $Repo --workflow $Workflow --branch $Branch --limit 1 --json "databaseId,url" | ConvertFrom-Json)[0]
    $runId = [int64]$run.databaseId
    $state = Wait-Run -RunId $runId

    $log = gh run view $runId -R $Repo --log
    $summaryLine = ($log | Select-String -Pattern "SUMMARY" -CaseSensitive:$false | Select-Object -Last 1).Line
    $errorLine = ($log | Select-String -Pattern "Failed for|Executor crashed|Not authenticated|Strict model selection failed" -CaseSensitive:$false | Select-Object -Last 1).Line

    if ($summaryLine) {
        if ($summaryLine -match '"processed":(\d+)') {
            $processedTotal += [int]$Matches[1]
        }
        if ($summaryLine -match '"failed":(\d+)') {
            $failedTotal += [int]$Matches[1]
        }
    }

    Write-Host ("Run {0} => conclusion={1}" -f $runId, $state.conclusion)
    if ($summaryLine) {
        Write-Host ("  {0}" -f $summaryLine)
    }
    if ($errorLine) {
        Write-Host ("  {0}" -f $errorLine)
    }

    if ($errorLine -match "Not authenticated|CHATGPT_UI required") {
        Write-Host "Stopping early: ChatGPT UI auth blocker detected."
        $blocked = $true
        break
    }
}

Write-Host ""
Write-Host "=== Backlog reprocess summary ==="
Write-Host ("Processed total: {0}" -f $processedTotal)
Write-Host ("Failed total: {0}" -f $failedTotal)
Write-Host ("Blocked by auth: {0}" -f $blocked)
