$Root = Split-Path -Parent $PSScriptRoot
$Core = Split-Path -Parent $Root

Write-Host "Starting Brain-Memory UI..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
  cd '$Root'
  `$env:BRAIN_MEMORY_ROOT='$Core'
  `$env:PYTHONPATH='$Core'
  python -m api.main
"@

Start-Sleep -Seconds 2

Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
  cd '$Root\frontend'
  if (-not (Test-Path node_modules)) { npm install }
  npm run dev
"@

Start-Sleep -Seconds 3
Start-Process "http://localhost:3000"
Write-Host "API: http://localhost:8000" -ForegroundColor Green
Write-Host "Web: http://localhost:3000" -ForegroundColor Green
