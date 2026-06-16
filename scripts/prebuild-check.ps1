# CNexus RC — verify toolchain before tauri build (~5–10 min compile)
$ErrorActionPreference = "Stop"
$fail = $false

Write-Host ""
Write-Host "=== CNexus pre-build check (RC) ===" -ForegroundColor Cyan
Write-Host ""

function Test-CommandVersion {
    param([string]$Name, [string[]]$Args)
    try {
        $out = & $Name @Args 2>&1 | Select-Object -First 1
        Write-Host "[OK] $Name : $out" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] $Name : not runnable" -ForegroundColor Red
        $script:fail = $true
    }
}

Test-CommandVersion "cargo" @("--version")
Test-CommandVersion "rustc" @("--version")

foreach ($bin in @("cargo", "rustc", "link")) {
    $found = Get-Command $bin -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "[OK] where $bin : $($found.Source)" -ForegroundColor Green
        continue
    }
    if ($bin -eq "link") {
        $vsRoot = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio"
        $linkHint = Get-ChildItem -LiteralPath $vsRoot -Recurse -Filter link.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "Host[xX]64\\x64\\link\.exe$" } |
            Select-Object -First 1
        if ($linkHint) {
            Write-Host "[OK] where link : $($linkHint.FullName) (VS OK — run build via vcvars64 / Native Tools prompt)" -ForegroundColor Green
            continue
        }
        Write-Host "       Install Visual Studio Build Tools -> Desktop development with C++" -ForegroundColor Yellow
    }
    Write-Host "[FAIL] where $bin : not found" -ForegroundColor Red
    $script:fail = $true
}

$nsis = Get-Command makensis -ErrorAction SilentlyContinue
if (-not $nsis) {
    foreach ($candidate in @(
            "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
            "${env:ProgramFiles}\NSIS\makensis.exe"
        )) {
        if (Test-Path $candidate) {
            $nsisDir = Split-Path $candidate -Parent
            $env:PATH = "$nsisDir;$env:PATH"
            $nsis = Get-Command makensis -ErrorAction SilentlyContinue
            break
        }
    }
}
if (-not $nsis) {
    Write-Host "[FAIL] NSIS (makensis) not found - without NSIS you only get CNexus.exe, not *-setup.exe installer" -ForegroundColor Red
    Write-Host "       Run: powershell -File scripts/ensure-nsis.ps1" -ForegroundColor Yellow
    Write-Host "       Or install from https://nsis.sourceforge.io/Download" -ForegroundColor Yellow
    $script:fail = $true
} else {
    Write-Host "[OK] NSIS : $($nsis.Source)" -ForegroundColor Green
}

Write-Host ""
if ($fail) {
    Write-Host "Pre-build check FAILED. Fix toolchain before npm run tauri:build" -ForegroundColor Red
    exit 1
}

Write-Host "All checks passed. Safe to run: npm run tauri:build" -ForegroundColor Green
Write-Host ""
