# Brain-Memory G1 — lightweight mode (low CPU/RAM, no Ollama auto-start)
# Usage: powershell -ExecutionPolicy Bypass -File scripts/run_lite.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DataDir = if ($env:BM_MEMORY_DIR) { $env:BM_MEMORY_DIR } else { "C:\ProgramData\brain-memory-g1\data" }
$UiRoot = Join-Path $ProjectRoot "brain-memory-ui"

$env:BRAIN_MEMORY_ROOT = $ProjectRoot
$env:PYTHONPATH = $ProjectRoot
$env:BM_MEMORY_DIR = $DataDir
$env:BM_EMBEDDING_MODE = "hash"
$env:BM_CONFIG = "config/lite.json"

Write-Host "Brain-Memory G1 LITE" -ForegroundColor Cyan
Write-Host "  hash embedding only (no Ollama)"
Write-Host "  lite config: recall_top_k=6, multi_hop=off"
Write-Host "  data: $DataDir"
Write-Host ""
Write-Host "Start API only (no frontend):" -ForegroundColor Yellow
Write-Host "  cd brain-memory-ui; python -m api.main"
Write-Host ""
Write-Host "Stop API:" -ForegroundColor Yellow
Write-Host "  Get-Process python | Where-Object { `$_.Path -like '*python*' } | Stop-Process"

# Optional: start API in new window
$start = Read-Host "Start API now? [y/N]"
if ($start -eq "y") {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
        `$env:BRAIN_MEMORY_ROOT='$ProjectRoot'
        `$env:PYTHONPATH='$ProjectRoot'
        `$env:BM_MEMORY_DIR='$DataDir'
        `$env:BM_EMBEDDING_MODE='hash'
        cd '$UiRoot'
        python -m api.main
"@
    Write-Host "API starting on :8000" -ForegroundColor Green
}
