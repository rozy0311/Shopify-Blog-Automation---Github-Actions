param(
    [string]$Repo = "rozy0311/Shopify-Blog-Automation---Github-Actions",
    [string]$Branch = "feat/openai-first-gemini-fallback-chain",
    [string]$Workflow = "publish.yml",
    [int]$WaitRunnerMinutes = 30,
    [int]$WaitRunMinutes = 45,
    [string]$ExpectedLabel = "chatgpt-ui",
    [switch]$SkipDispatch
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false
$env:GH_PAGER = "cat"

function Get-Runners {
    $payload = gh api "repos/$Repo/actions/runners" | ConvertFrom-Json
    return @($payload.runners)
}

function Get-LatestRun {
    $runs = gh run list --repo $Repo --workflow $Workflow --branch $Branch --limit 1 --json databaseId,status,conclusion,url,displayTitle,createdAt | ConvertFrom-Json
    if (-not $runs -or $runs.Count -eq 0) {
        return $null
    }
    return $runs[0]
}

function Get-RunState([long]$RunId) {
    return (gh run view $RunId --repo $Repo --json status,conclusion,url,displayTitle,createdAt,updatedAt | ConvertFrom-Json)
}

function Get-RunJob([long]$RunId) {
    $jobs = (gh api "repos/$Repo/actions/runs/$RunId/jobs" | ConvertFrom-Json).jobs
    if (-not $jobs -or $jobs.Count -eq 0) {
        return $null
    }
    return $jobs[0]
}

function Write-Section([string]$Title) {
    Write-Host ""
    Write-Host "=== $Title ==="
}

Write-Section "Runner check"
$deadlineRunner = (Get-Date).AddMinutes($WaitRunnerMinutes)
$runnerReady = $false
while ((Get-Date) -lt $deadlineRunner) {
    $runners = Get-Runners
    $matching = @($runners | Where-Object {
            $_.os -eq "windows" -and $_.status -eq "online" -and $_.busy -eq $false -and ($_.labels | Where-Object { $_.name -eq $ExpectedLabel })
        })

    Write-Host ("Total runners: {0} | Matching online+idle windows/{1}: {2}" -f $runners.Count, $ExpectedLabel, $matching.Count)
    if ($matching.Count -gt 0) {
        $runnerReady = $true
        Write-Host ("Using runner candidate: {0}" -f $matching[0].name)
        break
    }

    Start-Sleep -Seconds 15
}

if (-not $runnerReady) {
    throw "No matching self-hosted Windows runner became online within $WaitRunnerMinutes minutes."
}

$run = $null
if (-not $SkipDispatch) {
    Write-Section "Dispatch smoke run"
    gh workflow run $Workflow --repo $Repo --ref $Branch -f mode=review -f start_at=1 -f max_items=1 -f reason='auto-monitor smoke test' | Out-Null
    Start-Sleep -Seconds 5
    $run = Get-LatestRun
}
else {
    $run = Get-LatestRun
}

if ($null -eq $run) {
    throw "No workflow run found to monitor."
}

$runId = [int64]$run.databaseId
Write-Host ("Monitoring run: {0} | {1}" -f $runId, $run.url)

Write-Section "Run monitor"
$deadlineRun = (Get-Date).AddMinutes($WaitRunMinutes)
while ((Get-Date) -lt $deadlineRun) {
    $state = Get-RunState -RunId $runId
    $job = Get-RunJob -RunId $runId

    if ($null -ne $job) {
        $labels = if ($job.labels) { ($job.labels -join ',') } else { '' }
        $runnerName = if ($job.runner_name) { $job.runner_name } else { '(unassigned)' }
        Write-Host ("Run {0}: status={1} conclusion={2} | job={3} | labels={4} | runner={5}" -f $runId, $state.status, $state.conclusion, $job.status, $labels, $runnerName)
    }
    else {
        Write-Host ("Run {0}: status={1} conclusion={2} | job=(not created yet)" -f $runId, $state.status, $state.conclusion)
    }

    if ($state.status -eq "completed") {
        Write-Section "Final result"
        Write-Host ("Run ID: {0}" -f $runId)
        Write-Host ("Conclusion: {0}" -f $state.conclusion)
        Write-Host ("URL: {0}" -f $state.url)
        if ($state.conclusion -ne "success") {
            Write-Host "Tip: gh run view $runId --repo $Repo --log"
        }
        exit 0
    }

    Start-Sleep -Seconds 15
}

throw "Timed out waiting for run $runId to complete within $WaitRunMinutes minutes."
