# Brain-Memory G1 — staging mode (GTBS shadow + capture pilot)
# Usage: powershell -ExecutionPolicy Bypass -File scripts/run_staging.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DataDir = if ($env:BM_MEMORY_DIR) { $env:BM_MEMORY_DIR } else { "C:\ProgramData\brain-memory-g1\staging" }
$UiRoot = Join-Path $ProjectRoot "brain-memory-ui"

$env:BRAIN_MEMORY_ROOT = $ProjectRoot
$env:PYTHONPATH = $ProjectRoot
$env:BM_MEMORY_DIR = $DataDir
$env:BM_EMBEDDING_MODE = "hash"
$env:BM_CONFIG = "config/staging.json"

Write-Host "Brain-Memory G1 STAGING" -ForegroundColor Cyan
Write-Host "  config: config/staging.json"
Write-Host "  GTBS shadow: ON (persist to observability/gtbs_shadow.jsonl)"
Write-Host "  GTBS capture pilot: ON (observability/gtbs_transactions.jsonl)"
Write-Host "  data: $DataDir"
Write-Host ""
    Write-Host "Divergence report:" -ForegroundColor Yellow
    Write-Host "  python scripts/gtbs_shadow_report.py --base-dir `"$DataDir`""
    Write-Host "  python scripts/phase_a_landscape_report.py --base-dir `"$DataDir`""
Write-Host "  python scripts/phase_b_weekly_report.py --base-dir `"$DataDir`" --record"
Write-Host "  python scripts/phase_c_monthly_report.py --base-dir `"$DataDir`" --record"
Write-Host "  python scripts/semantic_alignment_report.py --base-dir `"$DataDir`""
Write-Host "  python scripts/semantic_alignment_report.py --base-dir `"$DataDir`" --temporal --window-days 7"
Write-Host "  python scripts/semantic_alignment_report.py --base-dir `"$DataDir`" --fusion --window-days 7"
Write-Host "  python scripts/semantic_alignment_report.py --base-dir `"$DataDir`" --attractor --window-days 7"
Write-Host ""
Write-Host "Start API:" -ForegroundColor Yellow
Write-Host "  cd brain-memory-ui; python -m api.main"
Write-Host ""

$start = Read-Host "Start API now? [y/N]"
if ($start -eq "y") {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
        `$env:BRAIN_MEMORY_ROOT='$ProjectRoot'
        `$env:PYTHONPATH='$ProjectRoot'
        `$env:BM_MEMORY_DIR='$DataDir'
        `$env:BM_EMBEDDING_MODE='hash'
        `$env:BM_CONFIG='config/staging.json'
        cd '$UiRoot'
        python -m api.main
"@
    Write-Host "API starting (staging config)" -ForegroundColor Green
}
