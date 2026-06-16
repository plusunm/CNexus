# CNexus RC — full pre-build audit (non-destructive, no file deletes)
param(
    [switch]$SkipTests,
    [switch]$SkipToolchain
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$Frontend = Join-Path $Root "brain-memory-ui\frontend"
$TauriDir = Join-Path $Frontend "src-tauri"
$ReportDir = Join-Path $Root "packaging\prebuild-rc"
$ReportPath = Join-Path $ReportDir "LATEST_AUDIT.txt"

$fail = 0
$warn = 0
$pass = 0
$lines = New-Object System.Collections.Generic.List[string]

function Add-Line($s) { $lines.Add($s) | Out-Null }

function Pass($msg) {
    $script:pass++
    Add-Line "[PASS] $msg"
    Write-Host "[PASS] $msg" -ForegroundColor Green
}

function Warn($msg) {
    $script:warn++
    Add-Line "[WARN] $msg"
    Write-Host "[WARN] $msg" -ForegroundColor Yellow
}

function Fail($msg) {
    $script:fail++
    Add-Line "[FAIL] $msg"
    Write-Host "[FAIL] $msg" -ForegroundColor Red
}

function Read-Json($path) {
    Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CNexus RC Full Pre-Build Audit" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Add-Line "CNexus RC Full Pre-Build Audit"
Add-Line "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Add-Line "Root: $Root"
Add-Line ""

# --- 1. Toolchain ---
Add-Line "== 1. Toolchain =="
if ($SkipToolchain) {
    Warn "Toolchain check skipped (-SkipToolchain)"
} else {
    $checkScript = Join-Path $ScriptDir "prebuild-check.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $checkScript | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Warn "prebuild-check failed — use VS Native Tools / vcvars64 before tauri build"
    } else {
        Pass "Toolchain prebuild-check"
    }
}

# --- 2. Float / window ---
Add-Line ""
Add-Line "== 2. Float window =="
$floatScript = Join-Path $ScriptDir "prebuild-audit-float.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $floatScript | Out-Host
if ($LASTEXITCODE -ne 0) { Fail "Float audit failed" } else { Pass "Float audit" }

# --- 3. Version sync ---
Add-Line ""
Add-Line "== 3. Version sync =="
$versionFile = Join-Path $Root "VERSION"
if (-not (Test-Path $versionFile)) {
    Fail "VERSION file missing"
} else {
    $expected = (Get-Content $versionFile -Raw).Trim()
    Pass "VERSION = $expected"
    $versionTargets = @(
        @{ Path = Join-Path $Frontend "package.json"; Prop = "version" },
        @{ Path = Join-Path $TauriDir "tauri.conf.json"; Prop = "version" },
        @{ Path = Join-Path $TauriDir "Cargo.toml"; Prop = $null; Pattern = 'version\s*=\s*"([^"]+)"' },
        @{ Path = Join-Path $TauriDir "cnexus-runtime-sidecar\Cargo.toml"; Prop = $null; Pattern = 'version\s*=\s*"([^"]+)"' },
        @{ Path = Join-Path $Root "pyproject.toml"; Prop = $null; Pattern = 'version\s*=\s*"([^"]+)"' }
    )
    foreach ($t in $versionTargets) {
        if (-not (Test-Path $t.Path)) { Fail "missing $($t.Path)"; continue }
        $actual = $null
        if ($t.Prop) {
            $actual = (Read-Json $t.Path).$($t.Prop)
        } else {
            if ((Get-Content $t.Path -Raw) -match $t.Pattern) { $actual = $Matches[1] }
        }
        $label = $t.Path.Replace($Root + "\", "").Replace("\", "/")
        if ($actual -eq $expected) {
            Pass "$label version OK"
        } else {
            Fail "$label version '$actual' != '$expected'"
        }
    }
}

# --- 4. Lock files ---
Add-Line ""
Add-Line "== 4. Lock files =="
$locks = @(
    (Join-Path $Frontend "package-lock.json"),
    (Join-Path $TauriDir "Cargo.lock"),
    (Join-Path $TauriDir "cnexus-runtime-sidecar\Cargo.lock")
)
foreach ($l in $locks) {
    if (Test-Path $l) { Pass (Split-Path $l -Leaf) } else { Fail "missing $(Split-Path $l -Leaf)" }
}

# --- 5. Runtime bundle ---
Add-Line ""
Add-Line "== 5. Runtime bundle =="
$bundle = Join-Path $TauriDir "runtime-bundle"
$mainPy = Join-Path $bundle "app\brain-memory-ui\api\main.py"
$pyw = Join-Path $bundle "python\pythonw.exe"
$py = Join-Path $bundle "python\python.exe"
if (-not (Test-Path $mainPy)) {
    Warn "runtime-bundle missing — run: npm run bundle:runtime"
} else {
    Pass "runtime-bundle api/main.py"
    if (Test-Path $pyw) { Pass "pythonw.exe in bundle" }
    elseif (Test-Path $py) { Warn "only python.exe in bundle (prefer pythonw)" }
    else { Fail "no python in runtime-bundle" }
}

# --- 6. Sidecar externalBin ---
Add-Line ""
Add-Line "== 6. Sidecar binary =="
$sidecar = Join-Path $TauriDir "cnexus-runtime-x86_64-pc-windows-msvc.exe"
if (Test-Path $sidecar) { Pass "cnexus-runtime sidecar exe" } else { Fail "run npm run build:sidecar" }

# --- 7. Multiprocess source ---
Add-Line ""
Add-Line "== 7. Multiprocess modules =="
$modules = @(
    "src\runtime_sidecar.rs",
    "src\runtime_cleanup.rs",
    "src\boot_sequence.rs",
    "cnexus-runtime-sidecar\src\main.rs",
    "windows\hooks.nsh"
)
foreach ($m in $modules) {
    $p = Join-Path $TauriDir $m
    if (Test-Path $p) { Pass $m } else { Fail "missing $m" }
}
$bootTsx = Join-Path $Frontend "components\desktop\DesktopFloatBoot.tsx"
if (Test-Path $bootTsx) { Pass "DesktopFloatBoot.tsx" } else { Fail "DesktopFloatBoot.tsx missing" }

# --- 8. Contract / config ---
Add-Line ""
Add-Line "== 8. Contract docs =="
$contract = Join-Path $Root "brain-memory-ui\docs\RUNTIME_CONTRACT.md"
if (Test-Path $contract) { Pass "RUNTIME_CONTRACT.md" } else { Fail "RUNTIME_CONTRACT.md missing" }
$conf = Read-Json (Join-Path $TauriDir "tauri.conf.json")
if ($conf.bundle.externalBin -contains "cnexus-runtime") { Pass "externalBin cnexus-runtime" }
else { Fail "externalBin must include cnexus-runtime" }
if ($conf.bundle.resources -contains "runtime-bundle/") { Pass "resources runtime-bundle/" }
else { Fail "resources must include runtime-bundle/" }
if (Test-Path (Join-Path $bundle "app/data-templates/runtime-conflict-monitor.log")) {
    Pass "data-templates/runtime-conflict-monitor.log"
} else { Warn "conflict monitor template missing — rerun bundle:runtime" }

# --- 9. Frontend export ---
Add-Line ""
Add-Line "== 9. Frontend export =="
$outDesktop = Join-Path $Frontend "out\desktop.html"
if (Test-Path $outDesktop) { Pass "out/desktop.html" } else { Warn "run npm run build:tauri" }

# --- 10. Tests ---
Add-Line ""
Add-Line "== 10. Contract tests =="
if ($SkipTests) {
    Warn "Tests skipped (-SkipTests)"
} else {
    Push-Location $Frontend
    try {
        npm run test:demo 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Pass "test:demo" } else { Fail "test:demo" }
        npm run test:kernel-boundary 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { Pass "test:kernel-boundary" } else { Fail "test:kernel-boundary" }
    } finally {
        Pop-Location
    }
}

# --- 11. UPX heuristic ---
Add-Line ""
Add-Line "== 11. Packing / UPX =="
$releaseDir = Join-Path $TauriDir "target\release"
$upxFound = $false
if (Test-Path $releaseDir) {
    Get-ChildItem $releaseDir -Filter "*.exe" -ErrorAction SilentlyContinue | ForEach-Object {
        $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
        $text = [System.Text.Encoding]::ASCII.GetString($bytes)
        if ($text -match "UPX!") { $upxFound = $true; Fail "UPX detected in $($_.Name)" }
    }
}
if (-not $upxFound) { Pass "No UPX signature in release exes (if present)" }

# --- 12. Port / process hygiene ---
Add-Line ""
Add-Line "== 12. Port 8000 hygiene =="
try {
    $listening = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($listening) {
        Warn "Port 8000 in use (PID $($listening.OwningProcess)) — run kill-cnexus-runtime.ps1 before build test"
    } else {
        Pass "Port 8000 free"
    }
} catch {
    Warn "Could not query port 8000"
}

# --- Summary ---
Add-Line ""
Add-Line "========================================"
Add-Line "SUMMARY: PASS=$pass WARN=$warn FAIL=$fail"
Add-Line "========================================"

if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
}
$lines | Set-Content -Path $ReportPath -Encoding UTF8
Write-Host ""
Write-Host "Report: $ReportPath" -ForegroundColor Cyan

if ($fail -gt 0) {
    Write-Host "AUDIT FAILED ($fail failures, $warn warnings)" -ForegroundColor Red
    exit 1
}
if ($warn -gt 0) {
    Write-Host "AUDIT PASSED WITH WARNINGS ($warn warnings)" -ForegroundColor Yellow
    exit 0
}
Write-Host "AUDIT PASSED" -ForegroundColor Green
exit 0
