# CNexus dev launcher - API + frontend + browser (ASCII-safe for PowerShell 5.1)
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$UiRoot = Join-Path $RepoRoot "brain-memory-ui"
$Frontend = Join-Path $UiRoot "frontend"
$HomeUrl = "http://localhost:3000/shell?layout=overview"
$LaunchDir = Join-Path $env:TEMP "cnexus-launch"

if (-not (Test-Path (Join-Path $UiRoot "api\main.py"))) {
    Write-Host "[ERROR] api\main.py not found under: $UiRoot" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $LaunchDir | Out-Null

function Write-LauncherCmd {
    param([string]$Name, [string[]]$Lines)
    $path = Join-Path $LaunchDir $Name
    $content = ($Lines -join "`r`n") + "`r`n"
    [System.IO.File]::WriteAllText($path, $content, [System.Text.UTF8Encoding]::new($false))
    return $path
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CNexus - start API + frontend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/5] Stop old processes..." -ForegroundColor Gray
& (Join-Path $RepoRoot "scripts\kill-cnexus-runtime.ps1")
Start-Sleep -Seconds 2

Write-Host "[2/5] Start API :8000..." -ForegroundColor Gray
$apiCmd = Write-LauncherCmd "cnexus-api.cmd" @(
    "@echo off"
    "chcp 65001 >nul"
    "title CNexus API"
    "set `"BRAIN_MEMORY_ROOT=$RepoRoot`""
    "set `"PYTHONPATH=$UiRoot;$RepoRoot`""
    "set CNEXUS_MINIMAL_BOOT=1"
    "set CNEXUS_CONTROL_PLANE_ISOLATION=1"
    "set CNEXUS_AUTO_RUNTIME_WARM=1"
    "cd /d `"$UiRoot`""
    "echo CNexus API http://127.0.0.1:8000"
    "python -m api.main"
    "pause"
)
Start-Process cmd.exe -ArgumentList @("/k", $apiCmd) -WindowStyle Normal

Write-Host "[3/5] Wait for API..." -ForegroundColor Gray
$apiReady = $false
for ($i = 1; $i -le 20; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/v1/system/ready" -TimeoutSec 2 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $apiReady = $true; break }
    } catch { }
    Write-Host "      waiting API $i/20..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 1
}
if ($apiReady) {
    Write-Host "      API ready" -ForegroundColor Green
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8000/v1/system/warm_runtime" -Method POST -TimeoutSec 5 -UseBasicParsing | Out-Null
        Write-Host "      runtime warm started" -ForegroundColor Green
    } catch {
        Write-Host "      [WARN] runtime warm trigger failed - data endpoints may 503 briefly" -ForegroundColor Yellow
    }
} else {
    Write-Host "      [WARN] API not ready - check CNexus API window" -ForegroundColor Yellow
}

Write-Host "[4/5] Start frontend :3000..." -ForegroundColor Gray
$uiCmd = Write-LauncherCmd "cnexus-ui.cmd" @(
    "@echo off"
    "chcp 65001 >nul"
    "title CNexus UI"
    "cd /d `"$Frontend`""
    "if not exist node_modules npm install --no-fund --no-audit"
    "node scripts/write-cnexus-config.mjs"
    "echo CNexus UI $HomeUrl"
    "npm run dev"
    "pause"
)
Start-Process cmd.exe -ArgumentList @("/k", $uiCmd) -WindowStyle Normal

Write-Host "[5/5] Wait for frontend compile..." -ForegroundColor Gray
$feReady = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:3000/shell" -TimeoutSec 3 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $feReady = $true; break }
    } catch { }
    Write-Host "      waiting frontend $i/30..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 2
}
if ($feReady) {
    Write-Host "      frontend ready" -ForegroundColor Green
} else {
    Write-Host "      [WARN] frontend still compiling - refresh browser later" -ForegroundColor Yellow
}

Start-Process $HomeUrl
Write-Host ""
Write-Host "Browser opened: $HomeUrl" -ForegroundColor Green
Write-Host "Close CNexus API / CNexus UI windows to stop." -ForegroundColor Gray
Write-Host ""
