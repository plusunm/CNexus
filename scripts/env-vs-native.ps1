# Activate VS x64 Native Tools context and verify cl/link (CNexus build readiness)
param(
    [switch]$DotSource,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir

function Find-VcVars64 {
    $candidates = @(
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"),
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"),
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"),
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build\vcvars64.bat"),
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return (Resolve-Path $c).Path }
    }
    $found = Get-ChildItem "${env:ProgramFiles(x86)}\Microsoft Visual Studio" -Recurse -Filter "vcvars64.bat" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "\\VC\\Auxiliary\\Build\\vcvars64\.bat$" } |
        Select-Object -First 1
    if ($found) { return $found.FullName }
    return $null
}

function Import-VcVarsToSession {
    param([string]$VcVarsPath)
    $lines = cmd /c "`"$VcVarsPath`" >nul 2>&1 && set"
    foreach ($line in $lines) {
        if ($line -match "^([^=]+)=(.*)$") {
            $name = $matches[1]
            $value = $matches[2]
            Set-Item -Path "env:$name" -Value $value
        }
    }
}

function Test-ClLinkInProcess {
    $cl = Get-Command cl -ErrorAction SilentlyContinue
    $link = Get-Command link -ErrorAction SilentlyContinue
    return @{
        cl = [bool]$cl
        link = [bool]$link
        cl_path = if ($cl) { $cl.Source } else { $null }
        link_path = if ($link) { $link.Source } else { $null }
    }
}

$vcvars = Find-VcVars64
if (-not $vcvars) {
    Write-Host "FAIL: vcvars64.bat not found — install VS Build Tools (C++ workload)" -ForegroundColor Red
    exit 1
}

if ($DotSource) {
    Import-VcVarsToSession -VcVarsPath $vcvars
    $check = Test-ClLinkInProcess
    if (-not $Quiet) {
        Write-Host "VS Native context loaded from:" -ForegroundColor Cyan
        Write-Host "  $vcvars"
        Write-Host "  cl:   $($check.cl_path)" -ForegroundColor $(if ($check.cl) { "Green" } else { "Red" })
        Write-Host "  link: $($check.link_path)" -ForegroundColor $(if ($check.link) { "Green" } else { "Red" })
    }
    if ($check.cl -and $check.link) {
        if (-not $Quiet) { Write-Host "ready: true" -ForegroundColor Green }
        return
    }
    Write-Host "ready: false (cl/link still missing after vcvars)" -ForegroundColor Red
    exit 1
}

# Default: run toolchain check inside a fresh vcvars-enabled cmd (works from npm / Cursor)
$toolchainScript = Join-Path $ScriptDir "prebuild-toolchain-check.ps1"
$cmd = @"
call "$vcvars" >nul 2>&1
if errorlevel 1 exit /b 1
where cl >nul 2>&1 || exit /b 2
where link >nul 2>&1 || exit /b 3
powershell -NoProfile -ExecutionPolicy Bypass -File "$toolchainScript" -Quiet
exit /b %ERRORLEVEL%
"@

$exitCode = 0
cmd /c $cmd
$exitCode = $LASTEXITCODE

if (-not $Quiet) {
    Write-Host ""
    if ($exitCode -eq 0) {
        Write-Host "env:vs-native -> ready: true" -ForegroundColor Green
        Write-Host ""
        Write-Host "To activate THIS PowerShell session:" -ForegroundColor Cyan
        Write-Host "  . `"$($ScriptDir)\env-vs-native.ps1`" -DotSource"
        Write-Host ""
        Write-Host "Or run full preflight in VS context:" -ForegroundColor Cyan
        Write-Host "  npm run prebuild:vs-preflight"
    } else {
        Write-Host "env:vs-native -> ready: false (exit=$exitCode)" -ForegroundColor Red
        if ($exitCode -eq 2) { Write-Host "  cl.exe not on PATH after vcvars64" -ForegroundColor Yellow }
        if ($exitCode -eq 3) { Write-Host "  link.exe not on PATH after vcvars64" -ForegroundColor Yellow }
        Write-Host ""
        Write-Host "vcvars64: $vcvars" -ForegroundColor Gray
    }
}

exit $exitCode
