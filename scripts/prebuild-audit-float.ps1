# CNexus float + runtime pre-build audit (non-destructive)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "brain-memory-ui\frontend"
$tauriDir = Join-Path $frontend "src-tauri"
$fail = $false

function Fail($msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    $script:fail = $true
}

function Pass($msg) {
    Write-Host "[OK] $msg" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== CNexus float pre-build audit ===" -ForegroundColor Cyan
Write-Host ""

# tauri.conf.json window constraints
$confPath = Join-Path $tauriDir "tauri.conf.json"
if (-not (Test-Path $confPath)) {
    Fail "missing tauri.conf.json"
} else {
    $conf = Get-Content $confPath -Raw | ConvertFrom-Json
    $float = $conf.app.windows | Where-Object { $_.label -eq "float" } | Select-Object -First 1
    if (-not $float) {
        Fail "float window missing in tauri.conf.json"
    } else {
        if ($float.width -ne 360 -or $float.height -ne 228) {
            Fail "float window must be 360x228 (got $($float.width)x$($float.height))"
        } else { Pass "float size 360x228" }

        if ($float.visible -ne $false) {
            Fail "float.visible must be false (load-then-show)"
        } else { Pass "float.visible=false" }

        foreach ($key in @("decorations", "transparent", "alwaysOnTop")) {
            if ($float.$key -ne $false -and $key -eq "decorations") { }
        }
        if ($float.decorations -ne $false) { Fail "float.decorations must be false" } else { Pass "float.decorations=false" }
        if ($float.transparent -ne $true) { Fail "float.transparent must be true" } else { Pass "float.transparent=true" }
        if ($float.alwaysOnTop -ne $true) { Fail "float.alwaysOnTop must be true" } else { Pass "float.alwaysOnTop=true" }
    }

    if ($conf.build.frontendDist -ne "../out") {
        Fail "frontendDist should be ../out"
    } else { Pass "frontendDist=../out" }
}

# Sidecar binary for externalBin
$sidecar = Join-Path $tauriDir "cnexus-runtime-x86_64-pc-windows-msvc.exe"
if (-not (Test-Path $sidecar)) {
    Fail "sidecar missing — run npm run build:sidecar"
} else { Pass "cnexus-runtime sidecar present" }

# Boot modules
foreach ($rel in @(
    "src\boot_sequence.rs",
    "src\runtime_cleanup.rs",
    "windows\hooks.nsh"
)) {
    $p = Join-Path $tauriDir $rel
    if (-not (Test-Path $p)) { Fail "missing $rel" } else { Pass "found $rel" }
}

$bootTsx = Join-Path $frontend "components\desktop\DesktopFloatBoot.tsx"
if (-not (Test-Path $bootTsx)) { Fail "missing DesktopFloatBoot.tsx" } else { Pass "found DesktopFloatBoot.tsx" }

# Static export (optional if not built yet)
$outDesktop = Join-Path $frontend "out\desktop.html"
if (-not (Test-Path $outDesktop)) {
    Write-Host "[WARN] out/desktop.html missing — run npm run build:desktop before final bundle" -ForegroundColor Yellow
} else {
    Pass "out/desktop.html exists"
    $staticDir = Join-Path $frontend "out\_next\static"
    if (-not (Test-Path $staticDir)) { Fail "out/_next/static missing" } else { Pass "out/_next/static exists" }
}

# No UPX on release binaries (heuristic)
$releaseDir = Join-Path $tauriDir "target\release"
if (Test-Path $releaseDir) {
    Get-ChildItem $releaseDir -Filter "*.exe" -ErrorAction SilentlyContinue | ForEach-Object {
        $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
        $text = [System.Text.Encoding]::ASCII.GetString($bytes)
        if ($text -match "UPX!") {
            Fail "$($_.Name) appears UPX-packed — forbidden for UI/runtime"
        }
    }
    if (-not $fail) { Pass "no UPX signature in release exes (if present)" }
}

Write-Host ""
if ($fail) {
    Write-Host "Float pre-build audit FAILED" -ForegroundColor Red
    exit 1
}
Write-Host "Float pre-build audit passed" -ForegroundColor Green
Write-Host ""
