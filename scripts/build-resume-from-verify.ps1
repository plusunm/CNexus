# Resume CNexus installer build after Next.js + bundle succeeded but tauri:build:vs exited -1.
# Usage: powershell -File scripts/build-resume-from-verify.ps1
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Frontend = Join-Path $RepoRoot "brain-memory-ui\frontend"
$RunVs = Join-Path $RepoRoot "scripts\run-in-vs-native.ps1"

Set-Location $Frontend

Write-Host "=== STAGE: verify:runtime-bundle ===" -ForegroundColor Cyan
npm run verify:runtime-bundle
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== STAGE: build:sidecar ===" -ForegroundColor Cyan
npm run build:sidecar
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "=== STAGE: tauri build (VS native) ===" -ForegroundColor Cyan
$cmd = "cd /d `"$Frontend`" && npx tauri build"
& powershell -NoProfile -ExecutionPolicy Bypass -File $RunVs $cmd
exit $LASTEXITCODE
