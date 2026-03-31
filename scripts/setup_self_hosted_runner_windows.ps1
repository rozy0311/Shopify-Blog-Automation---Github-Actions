param(
    [string]$Repo = "rozy0311/Shopify-Blog-Automation---Github-Actions",
    [string]$RepoDir = "$env:USERPROFILE\Shopify-Blog-Automation---Github-Actions",
    [string]$RunnerDir = "$env:USERPROFILE\actions-runner-chatgpt-ui",
    [string]$RunnerName = "$env:COMPUTERNAME-chatgpt-ui",
    [string]$RunnerLabels = "self-hosted,windows,chatgpt-ui"
)

$ErrorActionPreference = "Stop"

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

Write-Host "[1/8] Validating prerequisites"
Require-Command "gh"
Require-Command "git"
Require-Command "node"
Require-Command "npm"

& gh auth status | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "gh is not authenticated. Run: gh auth login"
}

Write-Host "[2/8] Preparing repository at $RepoDir"
if (-not (Test-Path "$RepoDir\.git")) {
    git clone "https://github.com/$Repo.git" "$RepoDir"
}

Set-Location $RepoDir

Write-Host "[3/8] Installing Node dependencies and Playwright"
npm ci
npx playwright install chromium

Write-Host "[4/8] Resolving latest GitHub Actions runner release"
$runnerVersion = (& gh api repos/actions/runner/releases/latest --jq '.tag_name').TrimStart('v')
if (-not $runnerVersion) {
    throw "Could not resolve GitHub Actions runner version"
}

Write-Host "[5/8] Downloading runner v$runnerVersion"
New-Item -ItemType Directory -Path $RunnerDir -Force | Out-Null
Set-Location $RunnerDir
$runnerZip = "actions-runner-win-x64-$runnerVersion.zip"
if (-not (Test-Path $runnerZip)) {
    Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/download/v$runnerVersion/$runnerZip" -OutFile $runnerZip
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
if (-not (Test-Path "$RunnerDir\config.cmd")) {
    [System.IO.Compression.ZipFile]::ExtractToDirectory((Join-Path $RunnerDir $runnerZip), $RunnerDir)
}

Write-Host "[6/8] Creating registration token"
$registrationToken = (& gh api -X POST "repos/$Repo/actions/runners/registration-token" --jq '.token')
if (-not $registrationToken) {
    throw "Failed to get runner registration token"
}

Write-Host "[7/8] Configuring runner"
cmd /c "config.cmd --unattended --url https://github.com/$Repo --token $registrationToken --name $RunnerName --labels $RunnerLabels --work _work --replace"
if ($LASTEXITCODE -ne 0) {
    throw "Runner configuration failed"
}

Write-Host "[8/8] Installing and starting runner service"
cmd /c "svc.cmd install"
if ($LASTEXITCODE -ne 0) {
    throw "Runner service install failed"
}
cmd /c "svc.cmd start"
if ($LASTEXITCODE -ne 0) {
    throw "Runner service start failed"
}

Write-Host "Setup complete."
Write-Host ""
Write-Host "Next steps on this Windows runner:"
Write-Host "1) Bootstrap ChatGPT login:"
Write-Host "   Set-Location $RepoDir"
Write-Host "   node ui-automation/scripts/chatgpt_persistent_bootstrap.mjs"
Write-Host ""
Write-Host "2) Upload storage-state secret from a trusted machine:"
Write-Host "   Get-Content .chatgpt-storageState.json.b64.txt -Raw | gh secret set CHATGPT_UI_STORAGE_STATE_B64 --repo $Repo"
