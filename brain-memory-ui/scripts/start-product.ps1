# CNexus Product — UI only (Demo mode, no backend required)
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "frontend"

Write-Host "CNexus Product (standalone UI)" -ForegroundColor Cyan
Set-Location $Frontend
if (-not (Test-Path node_modules)) { npm install }
Write-Host "Open http://localhost:3000 — choose Demo or Connect Runtime" -ForegroundColor Green
npm run dev
