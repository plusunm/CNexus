# Verify src-tauri/runtime-bundle is complete before tauri build / installer
$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Resolve-Path (Join-Path $ScriptDir "..")
$Bundle = Join-Path $Root "brain-memory-ui/frontend/src-tauri/runtime-bundle"

$required = @(
    "app/brain-memory-ui/api/main.py"
    "app/cnexus-config.json"
    "app/ir_kernel/__init__.py"
    "app/data-templates/runtime-conflict-monitor.log"
    "app/data-templates/runtime-conflict-monitor.README.txt"
    "python/python.exe"
    "python/python311.zip"
)

function Resolve-BundleSitePackages {
    param([Parameter(Mandatory)][string]$BundleRoot)
    $default = Join-Path $BundleRoot "python/Lib/site-packages"
    $pth = Join-Path $BundleRoot "python/python311._pth"
    if (Test-Path $pth) {
        $line = Get-Content $pth | Where-Object { $_ -match 'site-packages' } | Select-Object -First 1
        if ($line) {
            $rel = ($line -replace '\\', '/').Trim()
            $candidate = Join-Path $BundleRoot ("python/" + $rel.Replace('\', '/'))
            if (Test-Path $candidate) { return $candidate }
        }
    }
    $fresh = Get-ChildItem (Join-Path $BundleRoot "python/Lib") -Directory -Filter "site-packages.fresh.*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($fresh) { return $fresh.FullName }
    return $default
}

$sitePackages = Resolve-BundleSitePackages -BundleRoot $Bundle

Write-Host ""
Write-Host "=== CNexus runtime-bundle verify ===" -ForegroundColor Cyan

if (-not (Test-Path $Bundle)) {
    Write-Host "[FAIL] runtime-bundle missing: $Bundle" -ForegroundColor Red
    Write-Host "       Run: npm run bundle:runtime" -ForegroundColor Yellow
    exit 1
}

$missing = @()
foreach ($rel in $required) {
    $path = Join-Path $Bundle $rel
    if (Test-Path $path) {
        Write-Host "[OK] $rel" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $rel" -ForegroundColor Red
        $missing += $rel
    }
}

foreach ($name in @('fastapi', 'brain_memory', 'core')) {
    $path = Join-Path $sitePackages $name
    $label = $path.Replace($Bundle, 'runtime-bundle').TrimStart('\', '/')
    if (Test-Path $path) {
        Write-Host "[OK] $label" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $label" -ForegroundColor Red
        $missing += $label
    }
}

$pyw = Join-Path $Bundle "python/pythonw.exe"
if (Test-Path $pyw) {
    Write-Host "[OK] python/pythonw.exe" -ForegroundColor Green
} else {
    Write-Host "[WARN] python/pythonw.exe missing (will use python.exe)" -ForegroundColor Yellow
}

Write-Host ""
if ($missing.Count -gt 0) {
    Write-Host "runtime-bundle INCOMPLETE. Missing:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host "Run: npm run bundle:runtime" -ForegroundColor Yellow
    exit 1
}

$pyExe = Join-Path $Bundle "python/python.exe"
Write-Host "-> Smoke test bundled python..." -ForegroundColor Cyan
$prevHome = $env:PYTHONHOME
$env:PYTHONHOME = $null
$pyOut = & $pyExe -c "import encodings, fastapi; print('python runtime OK')" 2>&1
$env:PYTHONHOME = $prevHome
$pyOut | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] bundled python cannot start" -ForegroundColor Red
    Write-Host "       Hint: site-packages may be corrupt — close CNexus, delete runtime-bundle/python/Lib/site-packages, rerun bundle:runtime" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] python smoke test" -ForegroundColor Green

$appRoot = Join-Path $Bundle "app"
$workdir = Join-Path $appRoot "brain-memory-ui"
$site = $sitePackages
Write-Host "-> Smoke test API import (ir_kernel + api.main)..." -ForegroundColor Cyan
$prevHome = $env:PYTHONHOME
$prevPath = $env:PYTHONPATH
$prevRoot = $env:BRAIN_MEMORY_ROOT
$env:PYTHONHOME = $null
$env:BRAIN_MEMORY_ROOT = $appRoot
$env:PYTHONPATH = "$workdir;$appRoot;$site"
$apiOut = & $pyExe -c "import ir_kernel; import api.main; print('api import OK')" 2>&1
$env:PYTHONHOME = $prevHome
$env:PYTHONPATH = $prevPath
$env:BRAIN_MEMORY_ROOT = $prevRoot
$apiOut | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] bundled API cannot import (missing app layer?)" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] api.main import smoke test" -ForegroundColor Green

Write-Host "-> Smoke test conflict monitor module..." -ForegroundColor Cyan
$env:PYTHONHOME = $null
$env:BRAIN_MEMORY_ROOT = $appRoot
$env:PYTHONPATH = "$workdir;$appRoot;$site"
$cmOut = & $pyExe -c "from core.runtime.conflict_monitor import conflict_log_path, log_conflict_event; print(conflict_log_path())" 2>&1
$env:PYTHONHOME = $prevHome
$env:PYTHONPATH = $prevPath
$env:BRAIN_MEMORY_ROOT = $prevRoot
$cmOut | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] core.runtime.conflict_monitor missing from bundle wheel" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] conflict_monitor import smoke test" -ForegroundColor Green

Write-Host "-> Smoke test BrainMemoryRuntime inference bindings..." -ForegroundColor Cyan
$initPy = "import tempfile; from brain_memory.runtime import BrainMemoryRuntime; root=tempfile.mkdtemp(prefix='cnexus-bundle-smoke-'); runtime=BrainMemoryRuntime(base_dir=root, project_root=root); assert runtime.embedder is not None; assert runtime.llm_client._scheduler is not None or runtime.llm_client._plane is not None; print('runtime init bindings OK')"
$env:PYTHONHOME = $null
$env:BRAIN_MEMORY_ROOT = $appRoot
$env:PYTHONPATH = "$workdir;$appRoot;$site"
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$initOut = & $pyExe -c $initPy 2>&1
$initCode = $LASTEXITCODE
$ErrorActionPreference = $prevEap
$env:PYTHONHOME = $prevHome
$env:PYTHONPATH = $prevPath
$env:BRAIN_MEMORY_ROOT = $prevRoot
$initOut | ForEach-Object { Write-Host $_ }
if ($initCode -ne 0) {
    Write-Host "[FAIL] BrainMemoryRuntime init bindings broken in bundle wheel" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] runtime init bindings smoke test" -ForegroundColor Green

Write-Host "runtime-bundle OK for tauri build" -ForegroundColor Green
Write-Host ""
exit 0
