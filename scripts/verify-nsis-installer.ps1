# Verify CNexus NSIS installer integrity (size + optional makensis rebuild)
# UTF-8 with BOM for Windows PowerShell 5.1
param(
    [string]$InstallerPath = "",
    [int]$MinSizeMB = 70,
    [switch]$RebuildIfCorrupt
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $InstallerPath) {
    $InstallerPath = Join-Path $RepoRoot "brain-memory-ui\frontend\src-tauri\target\release\bundle\nsis\CNexus_0.1.0-alpha_x64-setup.exe"
}

function Test-InstallerSize {
    param([string]$Path, [int]$MinMB)
    if (-not (Test-Path $Path)) {
        return @{ Ok = $false; Reason = "missing"; SizeMB = 0 }
    }
    $sizeMB = [math]::Round((Get-Item $Path).Length / 1MB, 2)
    if ($sizeMB -lt $MinMB) {
        return @{ Ok = $false; Reason = "too_small"; SizeMB = $sizeMB }
    }
    return @{ Ok = $true; Reason = "ok"; SizeMB = $sizeMB }
}

$result = Test-InstallerSize -Path $InstallerPath -MinMB $MinSizeMB
if ($result.Ok) {
    Write-Host "[OK] NSIS installer: $InstallerPath ($($result.SizeMB) MB)" -ForegroundColor Green
    exit 0
}

Write-Host "[FAIL] NSIS installer corrupt or incomplete: $($result.Reason) ($($result.SizeMB) MB, need >= $MinSizeMB MB)" -ForegroundColor Red
Write-Host "       Path: $InstallerPath" -ForegroundColor Yellow

if (-not $RebuildIfCorrupt) {
    Write-Host "       Hint: re-run build and wait for NSIS (~3-5 min silence). Or: verify-nsis-installer.ps1 -RebuildIfCorrupt" -ForegroundColor Yellow
    exit 1
}

$nsisDir = Join-Path $RepoRoot "brain-memory-ui\frontend\src-tauri\target\release\nsis\x64"
$nsi = Join-Path $nsisDir "installer.nsi"
if (-not (Test-Path $nsi)) {
    Write-Host "[FAIL] installer.nsi missing — run full tauri build first" -ForegroundColor Red
    exit 1
}

$makensis = "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
if (-not (Test-Path $makensis)) {
    $makensis = "${env:ProgramFiles}\NSIS\makensis.exe"
}
if (-not (Test-Path $makensis)) {
    Write-Host "[FAIL] makensis.exe not found" -ForegroundColor Red
    exit 1
}

Write-Host "[..] Rebuilding NSIS installer (3-5 min)..." -ForegroundColor Cyan
Push-Location $nsisDir
try {
    & $makensis /V2 installer.nsi
    if ($LASTEXITCODE -ne 0) {
        throw "makensis failed (exit $LASTEXITCODE)"
    }
    $tmp = Join-Path $nsisDir "nsis-output.exe"
    if (-not (Test-Path $tmp)) {
        throw "nsis-output.exe not created"
    }
    $bundleDir = Split-Path $InstallerPath -Parent
    New-Item -ItemType Directory -Force -Path $bundleDir | Out-Null
    Copy-Item -Force $tmp $InstallerPath
}
finally {
    Pop-Location
}

$result = Test-InstallerSize -Path $InstallerPath -MinMB $MinSizeMB
if (-not $result.Ok) {
    Write-Host "[FAIL] Rebuild still invalid: $($result.SizeMB) MB" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] NSIS installer rebuilt: $InstallerPath ($($result.SizeMB) MB)" -ForegroundColor Green
exit 0
