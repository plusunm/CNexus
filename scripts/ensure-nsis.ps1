# Ensure NSIS (makensis) is available for Tauri *-setup.exe bundling
$ErrorActionPreference = "Stop"

function Find-Makensis {
    $cmd = Get-Command makensis -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    foreach ($path in @(
            "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
            "${env:ProgramFiles}\NSIS\makensis.exe"
        )) {
        if (Test-Path $path) { return (Resolve-Path $path).Path }
    }
    return $null
}

function Install-NsisSilent {
    $ver = "3.10"
    $setup = Join-Path $env:TEMP "nsis-$ver-setup.exe"
    $url = "https://sourceforge.net/projects/nsis/files/NSIS%203/$ver/nsis-$ver-setup.exe/download"

    Write-Host "-> Downloading NSIS $ver (required for *-setup.exe)..." -ForegroundColor Cyan

    $prevProxy = [System.Net.WebRequest]::DefaultWebProxy
    try {
        [System.Net.WebRequest]::DefaultWebProxy = $null
        if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
            & curl.exe --noproxy "*" -L --connect-timeout 60 --max-time 600 -o $setup $url
            if ($LASTEXITCODE -ne 0) { throw "curl download failed (exit $LASTEXITCODE)" }
        } else {
            Invoke-WebRequest -Uri $url -OutFile $setup -UseBasicParsing -TimeoutSec 600
        }
    } finally {
        [System.Net.WebRequest]::DefaultWebProxy = $prevProxy
    }

    if (-not (Test-Path $setup) -or (Get-Item $setup).Length -lt 500KB) {
        throw "NSIS download incomplete. Install manually from https://nsis.sourceforge.io/Download"
    }

    Write-Host "-> Installing NSIS silently..." -ForegroundColor Cyan
    $proc = Start-Process -FilePath $setup -ArgumentList "/S" -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        throw "NSIS installer exit code $($proc.ExitCode)"
    }
    Remove-Item $setup -Force -ErrorAction SilentlyContinue
}

$makensis = Find-Makensis
if (-not $makensis) {
    Install-NsisSilent
    $makensis = Find-Makensis
}

if (-not $makensis) {
    Write-Host "FAIL: makensis still not found after NSIS install" -ForegroundColor Red
    exit 1
}

$nsisDir = Split-Path $makensis -Parent
if ($env:PATH -notlike "*$nsisDir*") {
    $env:PATH = "$nsisDir;$env:PATH"
}

Write-Host "[OK] NSIS: $makensis" -ForegroundColor Green
exit 0
