param(
    [string]$Repo = "rozy0311/Shopify-Blog-Automation---Github-Actions",
    [string]$Branch = "feat/openai-first-gemini-fallback-chain",
    [string]$Workflow = "publish.yml",
    [int]$WaitRunnerMinutes = 120,
    [int]$WaitRunMinutes = 90,
    [int]$BacklogStartAt = 1,
    [int]$BacklogItems = 20,
    [int]$PollSeconds = 10,
    [string]$RunnerOs = "windows",
    [string]$ExpectedLabel = "chatgpt-ui"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
$env:GH_PAGER = "cat"

function Get-Runners {
    $payload = gh api "repos/$Repo/actions/runners" | ConvertFrom-Json
    return @($payload.runners)
}

function Wait-RunnerOnline {
    $deadline = (Get-Date).AddMinutes($WaitRunnerMinutes)
    while ((Get-Date) -lt $deadline) {
        $runners = Get-Runners
        $matching = @($runners | Where-Object {
                $_.os -eq $RunnerOs -and $_.status -eq "online" -and $_.busy -eq $false -and ($_.labels | Where-Object { $_.name -eq $ExpectedLabel })
            })

        Write-Host ("Runners total={0}, matching {1}/{2} online+idle={3}" -f $runners.Count, $RunnerOs, $ExpectedLabel, $matching.Count)
        if ($matching.Count -gt 0) {
            Write-Host ("Runner ready: {0}" -f $matching[0].name)
            return $true
        }

        Start-Sleep -Seconds 15
    }

    return $false
}

function Dispatch-OneRun([string]$Reason, [int]$StartAt, [int]$MaxItems) {
    gh workflow run $Workflow --repo $Repo --ref $Branch -f mode=review -f start_at=$StartAt -f max_items=$MaxItems -f reason=$Reason | Out-Null
    Start-Sleep -Seconds 5
    $run = (gh run list --repo $Repo --workflow $Workflow --branch $Branch --limit 1 --json databaseId, url, status | ConvertFrom-Json)[0]
    return $run
}

function Wait-Run([long]$RunId) {
    $deadline = (Get-Date).AddMinutes($WaitRunMinutes)
    while ((Get-Date) -lt $deadline) {
        $state = gh run view $RunId --repo $Repo --json status, conclusion, url | ConvertFrom-Json
        Write-Host ("Run {0}: status={1} conclusion={2}" -f $RunId, $state.status, $state.conclusion)
        if ($state.status -eq "completed") {
            return $state
        }
        Start-Sleep -Seconds $PollSeconds
    }

    throw "Timed out waiting for run $RunId"
}

function Get-SummaryFromLog([long]$RunId) {
    $log = gh run view $RunId --repo $Repo --log
    $summaryLine = ($log | Select-String -Pattern "SUMMARY" -CaseSensitive:$false | Select-Object -Last 1).Line
    $errorLine = ($log | Select-String -Pattern "Failed for|Executor crashed|Not authenticated|Strict model selection failed|CHATGPT_UI required" -CaseSensitive:$false | Select-Object -Last 1).Line

    $processed = 0
    $failed = 0
    if ($summaryLine -and $summaryLine -match '"processed":(\d+)') {
        $processed = [int]$Matches[1]
    }
    if ($summaryLine -and $summaryLine -match '"failed":(\d+)') {
        $failed = [int]$Matches[1]
    }

    return [pscustomobject]@{
        SummaryLine = $summaryLine
        ErrorLine   = $errorLine
        Processed   = $processed
        Failed      = $failed
    }
}

Write-Host ("=== Phase 1: Wait {0} runner ===" -f $RunnerOs)
if (-not (Wait-RunnerOnline)) {
    throw "No matching $RunnerOs self-hosted runner became available within timeout."
}

Write-Host "=== Phase 2: Smoke run ==="
$smoke = Dispatch-OneRun -Reason "autopilot-smoke" -StartAt 1 -MaxItems 1
$smokeId = [int64]$smoke.databaseId
$smokeState = Wait-Run -RunId $smokeId
$smokeSummary = Get-SummaryFromLog -RunId $smokeId
Write-Host ("Smoke summary: processed={0} failed={1}" -f $smokeSummary.Processed, $smokeSummary.Failed)
if ($smokeSummary.SummaryLine) { Write-Host $smokeSummary.SummaryLine }
if ($smokeSummary.ErrorLine) { Write-Host $smokeSummary.ErrorLine }

if ($smokeState.conclusion -ne "success" -or $smokeSummary.Processed -lt 1) {
    throw "Smoke run did not pass quality gate (needs success and processed>=1)."
}

Write-Host "=== Phase 3: Reprocess old failed backlog ==="
powershell -ExecutionPolicy Bypass -File scripts/reprocess_failed_backlog.ps1 -Repo $Repo -Branch $Branch -Workflow $Workflow -StartAt $BacklogStartAt -Items $BacklogItems -PollSeconds $PollSeconds
if ($LASTEXITCODE -ne 0) {
    throw "Backlog reprocess script failed"
}

Write-Host "=== Autopilot completed ==="
