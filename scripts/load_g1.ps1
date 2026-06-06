# Brain-Memory G1 — one-shot load (Windows)
# Usage: powershell -ExecutionPolicy Bypass -File scripts/load_g1.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DataDir = "C:\ProgramData\brain-memory-g1\data"
$UiRoot = Join-Path $ProjectRoot "brain-memory-ui"

New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

$env:BRAIN_MEMORY_ROOT = $ProjectRoot
$env:PYTHONPATH = $ProjectRoot
$env:BM_MEMORY_DIR = $DataDir

Write-Host "Brain-Memory G1 bootstrap" -ForegroundColor Cyan
Write-Host "  Project: $ProjectRoot"
Write-Host "  Data:    $DataDir"

# Python deps
python -c "import fastapi, lancedb, kuzu, httpx" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    pip install -r (Join-Path $ProjectRoot "requirements.txt") -q
}

# Ollama (optional — hash embedding fallback if unavailable)
$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollama) {
    try {
        Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 2 | Out-Null
        Write-Host "  Ollama:  running" -ForegroundColor Green
    } catch {
        Write-Host "  Ollama:  starting service..." -ForegroundColor Yellow
        Start-Process $ollama.Source -ArgumentList "serve" -WindowStyle Hidden -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
    }
} else {
    Write-Host "  Ollama:  not installed (using hash embedding fallback)" -ForegroundColor Yellow
}

# Runtime smoke test
python -c @"
from brain_memory import create_runtime
rt = create_runtime(project_root=r'$ProjectRoot')
mid = rt.capture('user', 'Brain-Memory G1 loaded successfully', layer='goal', importance=0.85)
print('runtime_ok', mid, 'data_dir', rt.base_dir)
"@

# API (:8000)
$apiUp = $false
try {
    Invoke-RestMethod "http://localhost:8000/health" -TimeoutSec 2 | Out-Null
    $apiUp = $true
} catch {}

if (-not $apiUp) {
    Write-Host "Starting API on :8000..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
        `$env:BRAIN_MEMORY_ROOT='$ProjectRoot'
        `$env:PYTHONPATH='$ProjectRoot'
        `$env:BM_MEMORY_DIR='$DataDir'
        cd '$UiRoot'
        python -m api.main
"@
    Start-Sleep -Seconds 4
}

# Frontend (:3000)
$feUp = $false
try {
    $r = Invoke-WebRequest "http://localhost:3000/" -TimeoutSec 2 -UseBasicParsing
    $feUp = ($r.StatusCode -eq 200)
} catch {}

if (-not $feUp) {
    Write-Host "Starting frontend on :3000..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
        cd '$UiRoot\frontend'
        if (-not (Test-Path node_modules)) { npm install }
        npm run dev
"@
    Start-Sleep -Seconds 5
}

# Verify
try {
    $h = Invoke-RestMethod "http://localhost:8000/health" -TimeoutSec 8
    Write-Host "API:       http://localhost:8000  ($($h.status))" -ForegroundColor Green
} catch {
    Write-Host "API:       failed to start — check brain-memory-ui terminal" -ForegroundColor Red
}

try {
    $c = (Invoke-WebRequest "http://localhost:3000/" -TimeoutSec 8 -UseBasicParsing).StatusCode
    Write-Host "Frontend:  http://localhost:3000  ($c)" -ForegroundColor Green
} catch {
    Write-Host "Frontend:  failed to start — check frontend terminal" -ForegroundColor Red
}

Write-Host "`nReady. Open http://localhost:3000" -ForegroundColor Green
