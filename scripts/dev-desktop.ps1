# CNexus desktop dev — hot reload, NO installer, NO uninstall
# Usage:
#   dev-desktop.ps1 browser   # fastest: browser http://localhost:3000/desktop
#   dev-desktop.ps1 tauri     # Tauri float window + hot reload (default)
param(
    [ValidateSet("browser", "tauri")]
    [string]$Mode = "tauri"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$UiRoot = Join-Path $RepoRoot "brain-memory-ui"
$Frontend = Join-Path $UiRoot "frontend"

function Test-CnexusApiHealthy {
    foreach ($path in @("/health", "/v1/health")) {
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000$path" -TimeoutSec 1.5 -UseBasicParsing
            if ($r.StatusCode -ne 200) { continue }
            $body = $r.Content.ToLowerInvariant()
            if ($body -match "cnexus" -or $body -match '"status"\s*:\s*"(ok|ready|warming)"') {
                return $true
            }
        } catch { }
    }
    return $false
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CNexus DEV (no pack, no uninstall)" -ForegroundColor Cyan
Write-Host "  Mode: $Mode" -ForegroundColor Gray
Write-Host "  Edit code -> save -> see changes in seconds" -ForegroundColor Gray
Write-Host "  Run desktop installer bat ONLY when ready to ship" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$apiAlreadyUp = Test-CnexusApiHealthy
if ($apiAlreadyUp) {
    Write-Host "[OK] Reusing existing CNexus API on :8000 (skip kill + restart)" -ForegroundColor Green
} else {
    & (Join-Path $RepoRoot "scripts\kill-cnexus-runtime.ps1")
    Start-Sleep -Seconds 1
    Write-Host "Port guard: cleared stale :8000 / :3000 listeners" -ForegroundColor Gray

    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        Write-Host "FAIL: python not found" -ForegroundColor Red
        exit 1
    }

    $apiPs1 = Join-Path $env:TEMP "cnexus-dev-api.ps1"
    @(
        "`$env:BRAIN_MEMORY_ROOT = '$RepoRoot'"
        "`$env:PYTHONPATH = '$RepoRoot'"
        "Set-Location '$UiRoot'"
        "Write-Host 'CNexus API dev :8000' -ForegroundColor Green"
        "python -m api.main"
    ) | Set-Content -Path $apiPs1 -Encoding UTF8

    Start-Process powershell -ArgumentList @(
        "-NoExit", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $apiPs1
    ) -WindowStyle Normal

    Write-Host "Waiting for API on :8000..." -ForegroundColor Gray
    $ready = $false
    for ($i = 0; $i -lt 40; $i++) {
        if (Test-CnexusApiHealthy) { $ready = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if ($ready) {
        Write-Host "[OK] API ready http://127.0.0.1:8000" -ForegroundColor Green
    } else {
        Write-Host "[WARN] API not healthy yet; UI may retry. Check API window." -ForegroundColor Yellow
    }
}

Set-Location $Frontend
if (-not (Test-Path "node_modules")) {
    Write-Host "First run: npm install..." -ForegroundColor Gray
    npm install --no-fund --no-audit
}

node scripts/write-cnexus-config.mjs | Out-Host

if ($Mode -eq "browser") {
    Write-Host ""
    Write-Host "Browser dev: http://localhost:3000/desktop" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop UI (API window stays open)" -ForegroundColor Gray
    Start-Process "http://localhost:3000/desktop"
    npm run dev
    exit 0
}

$iconIco = Join-Path $Frontend "src-tauri\icons\icon.ico"
if (-not (Test-Path $iconIco)) {
    Write-Host "First run: generating Tauri icons..." -ForegroundColor Gray
    npm run tauri:icons
}

Write-Host ""
Write-Host "Tauri dev: float window + hot reload" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop (API window stays open)" -ForegroundColor Gray
npx tauri dev
