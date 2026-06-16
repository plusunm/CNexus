# CNexus Build Toolchain Readiness — fail-fast before tauri:build
param(
    [switch]$Quiet,
    [switch]$JsonOnly
)

$ErrorActionPreference = "Continue"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$Frontend = Join-Path $Root "brain-memory-ui\frontend"
$ReportDir = Join-Path $Root "packaging\prebuild-rc"
$JsonPath = Join-Path $ReportDir "TOOLCHAIN_READY.json"
$TxtPath = Join-Path $ReportDir "LATEST_TOOLCHAIN.txt"

function Test-CmdExists($name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    return [bool]$cmd
}

function Get-CmdPath($name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Test-LinkAvailable {
    if (Test-CmdExists "link") { return @{ ok = $true; path = (Get-CmdPath "link") } }
    $vsRoot = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio"
    $linkHint = Get-ChildItem -LiteralPath $vsRoot -Recurse -Filter link.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "Host[xX]64\\x64\\link\.exe$" } |
        Select-Object -First 1
    if ($linkHint) {
        return @{ ok = $false; path = $linkHint.FullName; hint = "use VS x64 Native Tools or vcvars64.bat" }
    }
    return @{ ok = $false; path = $null; hint = "install VS Build Tools C++ workload" }
}

function Test-WindowsSdkHint {
    $kits = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    if (-not (Test-Path $kits)) { return $false }
    return [bool](Get-ChildItem $kits -Directory -ErrorAction SilentlyContinue | Select-Object -First 1)
}

function Test-NodeMajor($min = 20) {
    if (-not (Test-CmdExists "node")) { return @{ ok = $false; version = $null } }
    $v = (node -v 2>&1) -replace "^v", ""
    $major = 0
    if ($v -match "^(\d+)") { [int]::TryParse($Matches[1], [ref]$major) | Out-Null }
    return @{ ok = ($major -ge $min); version = $v }
}

function Test-TauriCli {
    Push-Location $Frontend
    try {
        $out = npx tauri --version 2>&1 | Select-Object -First 1
        $ok = $LASTEXITCODE -eq 0 -or ($out -match "tauri-cli")
        return @{ ok = $ok; version = [string]$out }
    } catch {
        return @{ ok = $false; version = $null }
    } finally {
        Pop-Location
    }
}

$link = Test-LinkAvailable
$node = Test-NodeMajor -min 20
$tauri = Test-TauriCli

$rustcVer = $null
$cargoVer = $null
$npmVer = $null
try { $rustcVer = (rustc --version 2>&1 | Select-Object -First 1) } catch { }
try { $cargoVer = (cargo --version 2>&1 | Select-Object -First 1) } catch { }
try { $npmVer = (npm -v 2>&1 | Select-Object -First 1) } catch { }

$checks = [ordered]@{
    cl = Test-CmdExists "cl"
    link = [bool]$link.ok
    msvc_path_cl = (Get-CmdPath "cl")
    msvc_path_link = if ($link.ok) { $link.path } else { $link.path }
    windows_sdk = (Test-WindowsSdkHint)
    rust = Test-CmdExists "rustc"
    cargo = Test-CmdExists "cargo"
    rustc_version = [string]$rustcVer
    cargo_version = [string]$cargoVer
    node = [bool]$node.ok
    node_version = $node.version
    npm = Test-CmdExists "npm"
    npm_version = [string]$npmVer
    tauri = [bool]$tauri.ok
    tauri_version = $tauri.version
}

$required = @("cl", "link", "rust", "cargo", "node", "npm", "tauri")
$checks.ready = -not ($required | Where-Object { -not $checks[$_] })

$doc = [ordered]@{
    at = (Get-Date).ToString("o")
    ready = $checks.ready
    checks = $checks
    hints = @()
}
if (-not $checks.cl -or -not $checks.link) {
    if ($link.hint) { $doc.hints += $link.hint }
    $vcvars = Get-ChildItem "${env:ProgramFiles(x86)}\Microsoft Visual Studio" -Recurse -Filter "vcvars64.bat" -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
    if ($vcvars) { $doc.hints += "vcvars64: $vcvars" }
}
if (-not $checks.windows_sdk) { $doc.hints += "Windows 10/11 SDK not detected under Program Files (x86)\Windows Kits\10" }

if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null }
$doc | ConvertTo-Json -Depth 6 | Set-Content -Path $JsonPath -Encoding UTF8

$txt = @(
    "CNexus TOOLCHAIN READINESS"
    "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    "READY: $($checks.ready)"
    ""
    "cl:      $($checks.cl)  $($checks.msvc_path_cl)"
    "link:    $($checks.link)  $($checks.msvc_path_link)"
    "Windows SDK dir: $($checks.windows_sdk)"
    "rustc:   $($checks.rust)  $($checks.rustc_version)"
    "cargo:   $($checks.cargo)  $($checks.cargo_version)"
    "node:    $($checks.node)  v$($checks.node_version)"
    "npm:     $($checks.npm)  v$($checks.npm_version)"
    "tauri:   $($checks.tauri)  $($checks.tauri_version)"
)
if ($doc.hints.Count -gt 0) {
    $txt += ""
    $txt += "Hints:"
    $doc.hints | ForEach-Object { $txt += "  - $_" }
}
$txt | Set-Content -Path $TxtPath -Encoding UTF8

if ($JsonOnly) {
    Get-Content $JsonPath -Raw
    exit $(if ($checks.ready) { 0 } else { 1 })
}

if (-not $Quiet) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host " CNexus TOOLCHAIN READINESS" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    foreach ($k in @("cl", "link", "windows_sdk", "rust", "cargo", "node", "npm", "tauri")) {
        $v = $checks[$k]
        $color = if ($v) { "Green" } else { "Red" }
        Write-Host ("[{0}] {1}" -f $(if ($v) { "OK" } else { "FAIL" }), $k) -ForegroundColor $color
    }
    Write-Host ""
    if ($checks.ready) {
        Write-Host "TOOLCHAIN READY — safe to run tauri:build" -ForegroundColor Green
    } else {
        Write-Host "TOOLCHAIN NOT READY — open VS x64 Native Tools before build" -ForegroundColor Red
        foreach ($h in $doc.hints) { Write-Host "  hint: $h" -ForegroundColor Yellow }
    }
    Write-Host ""
    Write-Host "Report: $JsonPath" -ForegroundColor Cyan
}

exit $(if ($checks.ready) { 0 } else { 1 })
