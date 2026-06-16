# Bundle CNexus Runtime for desktop installer (process 2 of 2).
# Output: brain-memory-ui/frontend/src-tauri/runtime-bundle/
# Requires: Python 3.11+, pip, network (first run downloads embeddable Python)

param(
    [switch]$SkipPythonDownload
)

$ErrorActionPreference = "Stop"

function Invoke-DirectWebRequest {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][string]$OutFile
    )
    $prevProxy = [System.Net.WebRequest]::DefaultWebProxy
    try {
        [System.Net.WebRequest]::DefaultWebProxy = $null
        for ($i = 1; $i -le 3; $i++) {
            try {
                if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
                    & curl.exe --noproxy "*" -L --connect-timeout 60 --max-time 600 -o $OutFile $Uri
                    if ($LASTEXITCODE -eq 0 -and (Test-Path $OutFile) -and ((Get-Item $OutFile).Length -gt 1MB)) {
                        return
                    }
                }
                Invoke-WebRequest -Uri $Uri -OutFile $OutFile -UseBasicParsing -TimeoutSec 600
                return
            } catch {
                Write-Warning "Download attempt $i of 3 failed: $($_.Exception.Message)"
                if ($i -lt 3) { Start-Sleep -Seconds 3 }
                else { throw }
            }
        }
    } finally {
        [System.Net.WebRequest]::DefaultWebProxy = $prevProxy
    }
}

function Invoke-PipDirect {
    param([Parameter(Mandatory)][string[]]$PipArgs)
    $saved = @{}
    foreach ($name in @(
            'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'PIP_PROXY'
        )) {
        if (Test-Path "Env:$name") { $saved[$name] = (Get-Item "Env:$name").Value }
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }
    $savedNoProxy = $env:NO_PROXY
    $savedNoProxyLower = $env:no_proxy
    $env:NO_PROXY = '*'
    $env:no_proxy = '*'
    try {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $pipOut = & pip @PipArgs 2>&1
        $ErrorActionPreference = $prevEap
        $pipOut | ForEach-Object { Write-Host $_ }
        $text = ($pipOut | Out-String)
        $code = $LASTEXITCODE
        if ($code -ne 0) {
            if ($text -match 'PermissionError|WinError 5|拒绝访问|Access is denied') {
                throw "pip install failed: runtime-bundle site-packages is locked. Exit CNexus completely, then rebuild."
            }
            if (($text -match 'pylance.*incompatible' -or $text -match 'dependency conflicts') -and $text -match 'Successfully installed') {
                Write-Warning "pip exit $code ignored (global pylance conflict is harmless for bundle target)"
            } elseif ($text -match 'Successfully installed' -and $text -notmatch 'Traceback') {
                Write-Warning "pip exit $code ignored (packages appear installed)"
            } else {
                exit $code
            }
        }
    } finally {
        foreach ($name in $saved.Keys) { Set-Item -Path "Env:$name" -Value $saved[$name] }
        if ($null -ne $savedNoProxy) { $env:NO_PROXY = $savedNoProxy } else { Remove-Item Env:NO_PROXY -ErrorAction SilentlyContinue }
        if ($null -ne $savedNoProxyLower) { $env:no_proxy = $savedNoProxyLower } else { Remove-Item Env:no_proxy -ErrorAction SilentlyContinue }
    }
}

$ScriptDir = $PSScriptRoot
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")

$BundleRoot = Join-Path $RepoRoot "brain-memory-ui/frontend/src-tauri/runtime-bundle"
$AppRoot = Join-Path $BundleRoot "app"
$PythonRoot = Join-Path $BundleRoot "python"
$SitePackages = Join-Path $PythonRoot "Lib/site-packages"

function Get-SitePackagesPthEntry {
    $entry = $SitePackages.Substring($PythonRoot.Length).TrimStart('\', '/')
    return $entry.Replace('/', '\')
}

function Switch-ToFreshSitePackagesTarget {
    $lib = Join-Path $PythonRoot "Lib"
    $stamp = Get-Date -Format 'yyyyMMddHHmmss'
    $script:SitePackages = Join-Path $lib "site-packages.fresh.$stamp"
    New-Item -ItemType Directory -Force -Path $script:SitePackages | Out-Null
    Write-Host "-> Locked tree bypass: using $script:SitePackages" -ForegroundColor Yellow
}
$WheelDir = Join-Path $BundleRoot "wheels"

function Get-ExcludedBuildProcessIds {
    $ids = [System.Collections.Generic.HashSet[int]]::new()
    $current = $PID
    while ($current) {
        [void]$ids.Add([int]$current)
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$current" -ErrorAction SilentlyContinue
        if (-not $proc -or $proc.ParentProcessId -eq 0) { break }
        $current = $proc.ParentProcessId
    }
    return $ids
}

function Stop-RuntimeBundleLockers {
    Write-Host "-> Stopping processes that may lock runtime-bundle..."
    & (Join-Path $ScriptDir "kill-cnexus-runtime.ps1") | Out-Host
    Start-Sleep -Seconds 2
    $excluded = Get-ExcludedBuildProcessIds
    foreach ($name in @('python', 'pythonw', 'cnexus-runtime', 'cnexus-product', 'CNexus')) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | ForEach-Object {
            if ($excluded.Contains($_.Id)) { return }
            Write-Host "  kill $name pid $($_.Id)"
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $excluded -notcontains $_.ProcessId -and
        $_.Name -in @('python.exe', 'pythonw.exe') -and
        $_.CommandLine -and (
            $_.CommandLine -match 'api\.main' -or
            $_.CommandLine -match 'uvicorn' -or
            ($_.CommandLine -match 'runtime-bundle' -and $_.CommandLine -notmatch 'pip\s')
        )
    } | ForEach-Object {
        Write-Host "  kill locker pid $($_.ProcessId) ($($_.Name))"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

function Clear-SitePackagesDir {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path $Path)) { return }

    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Remove-Item $Path -Recurse -Force -ErrorAction Stop
            return
        } catch {
            Write-Warning "site-packages delete attempt $attempt failed: $($_.Exception.Message)"
            Stop-RuntimeBundleLockers
        }
    }

    # Windows often blocks delete on loaded .pyd but allows rename — stage a fresh tree.
    $parent = Split-Path $Path -Parent
    $stamp = Get-Date -Format 'yyyyMMddHHmmss'
    $bakName = "site-packages.bak.$stamp"
    $bakPath = Join-Path $parent $bakName
    try {
        Rename-Item -Path $Path -NewName $bakName -Force -ErrorAction Stop
        Write-Host "-> Renamed locked site-packages to $bakName (pip will use a clean folder)" -ForegroundColor Yellow
    } catch {
        Write-Warning "Rename also failed: $($_.Exception.Message)"
        if ($Path -eq (Join-Path $PythonRoot "Lib/site-packages")) {
            Switch-ToFreshSitePackagesTarget
            return
        }
        throw @"
Cannot clear locked site-packages: $Path
Close CNexus (tray -> Exit), close empty CMD windows, then rerun build.
"@
    }

    Get-ChildItem $parent -Directory -Filter 'site-packages.bak.*' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip 1 |
        ForEach-Object {
            Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }
}

Write-Host "== CNexus runtime bundle =="
Write-Host "Repo:   $RepoRoot"
Write-Host "Bundle: $BundleRoot"

function Clear-BundleRoot {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path $Path)) { return }

    $lockHint = "Close CNexus completely (tray -> Exit) and kill any python.exe locking runtime-bundle, then rebuild."

    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Remove-Item $Path -Recurse -Force -ErrorAction Stop
            return
        } catch {
            Write-Warning "Cannot remove old runtime-bundle (attempt $attempt of 3): $($_.Exception.Message)"
            if ($attempt -lt 3) {
                Write-Host "-> Retrying in 2 seconds..."
                Start-Sleep -Seconds 2
            }
        }
    }

    Write-Warning "Full delete failed; trying partial cleanup (keep python/ if present)..."
    $keepPython = Test-Path (Join-Path $Path "python/python.exe")
    foreach ($child in @("wheels", "app")) {
        $target = Join-Path $Path $child
        if (Test-Path $target) {
            Remove-Item $target -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    Remove-Item (Join-Path $Path "python-embed.zip") -Force -ErrorAction SilentlyContinue
    if (-not $keepPython -and (Test-Path (Join-Path $Path "python"))) {
        Remove-Item (Join-Path $Path "python") -Recurse -Force -ErrorAction SilentlyContinue
    }
    if ($keepPython) {
        Write-Host "-> Kept existing python/ embed; will refresh app + wheels only."
    } else {
        Write-Host "-> Partial cleanup done; will reuse runtime-bundle folder."
    }
    return
}

function Prepare-BundleRoot {
    param([Parameter(Mandatory)][string]$Path)

    $existingPython = Test-Path (Join-Path $PythonRoot "python.exe")
    if ($existingPython) {
        Write-Host "-> Reusing python/ embed; refreshing app + wheels + site-packages only"
        foreach ($child in @("wheels", "app")) {
            $target = Join-Path $Path $child
            if (Test-Path $target) {
                Remove-Item $target -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
        if (Test-Path $SitePackages) {
            Clear-SitePackagesDir -Path $SitePackages
        }
        Remove-Item (Join-Path $Path "python-embed.zip") -Force -ErrorAction SilentlyContinue
        return
    }

    Clear-BundleRoot -Path $Path
}

Prepare-BundleRoot -Path $BundleRoot
Stop-RuntimeBundleLockers
New-Item -ItemType Directory -Force -Path $AppRoot, $PythonRoot, $SitePackages, $WheelDir | Out-Null
$refreshDeps = Test-Path (Join-Path $PythonRoot "python.exe")

function Write-PythonPth {
    param([Parameter(Mandatory)][string]$Dest)
    $pthPath = Join-Path $Dest "python311._pth"
    $siteEntry = Get-SitePackagesPthEntry
    @(
        "python311.zip",
        ".",
        "..\app\brain-memory-ui",
        "..\app",
        $siteEntry,
        "import site"
    ) | Set-Content $pthPath -Encoding ASCII
}

function Install-EmbeddedPythonFromZip {
    param(
        [Parameter(Mandatory)][string]$Dest,
        [Parameter(Mandatory)][string]$EmbedZip,
        [Parameter(Mandatory)][string[]]$EmbedUrls
    )
    $embedMinBytes = 10MB
    $cacheDir = Split-Path $EmbedZip -Parent
    New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
    $haveCachedZip = (Test-Path $EmbedZip) -and ((Get-Item $EmbedZip).Length -ge $embedMinBytes)
    if ($haveCachedZip) {
        Write-Host "-> Using cached Python embed zip ($EmbedZip)"
    } else {
        if (Test-Path $EmbedZip) {
            Write-Warning "Incomplete embed zip ($EmbedZip) — re-downloading"
            Remove-Item $EmbedZip -Force -ErrorAction SilentlyContinue
        }
        Write-Host "-> Downloading Python 3.11 embeddable..."
        $downloaded = $false
        foreach ($url in $EmbedUrls) {
            try {
                Write-Host "   try: $url"
                Invoke-DirectWebRequest -Uri $url -OutFile $EmbedZip
                if ((Test-Path $EmbedZip) -and (Get-Item $EmbedZip).Length -ge $embedMinBytes) {
                    $downloaded = $true
                    break
                }
            } catch {
                Write-Warning "Download failed: $($_.Exception.Message)"
            }
            Remove-Item $EmbedZip -Force -ErrorAction SilentlyContinue
        }
        if (-not $downloaded) {
            throw "Could not download Python embed zip from any mirror."
        }
    }
    if (-not (Test-Path $EmbedZip) -or (Get-Item $EmbedZip).Length -lt $embedMinBytes) {
        throw "Incomplete embed zip (need >= 10MB). Delete $EmbedZip and retry."
    }
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    $expandZip = Join-Path $env:TEMP "cnexus-python-embed-expand-$(Get-Random).zip"
    Copy-Item -Force $EmbedZip $expandZip
    try {
        Expand-Archive -Path $expandZip -DestinationPath $Dest -Force
    } finally {
        Remove-Item $expandZip -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path (Join-Path $Dest "python311.zip"))) {
        throw "Embed zip expanded but python311.zip missing in $Dest"
    }
}

if (-not $SkipPythonDownload) {
    $EmbedZip = Join-Path $RepoRoot "scripts/cache/python-3.11.9-embed-amd64.zip"
    $EmbedUrls = @(
        "https://registry.npmmirror.com/-/binary/python/3.11.9/python-3.11.9-embed-amd64.zip",
        "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
    )
    $needEmbed = $false
    if (-not (Test-Path (Join-Path $PythonRoot "python.exe"))) {
        $needEmbed = $true
    } elseif (-not (Test-Path (Join-Path $PythonRoot "python311.zip"))) {
        Write-Warning "Broken python embed (missing python311.zip) — reinstalling from embed zip"
        Get-ChildItem $PythonRoot -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        $needEmbed = $true
    }

    if ($needEmbed) {
        $localEmbed = $null
        if ($env:CNEXUS_LOCAL_PYTHON311 -and (Test-Path $env:CNEXUS_LOCAL_PYTHON311)) {
            $localRoot = Split-Path $env:CNEXUS_LOCAL_PYTHON311 -Parent
            if (Test-Path (Join-Path $localRoot "python311.zip")) {
                $localEmbed = $localRoot
            }
        }
        if ($localEmbed) {
            Write-Host "-> Copying embeddable Python from $localEmbed"
            New-Item -ItemType Directory -Force -Path $PythonRoot | Out-Null
            Copy-Item -Force "$localEmbed\*" $PythonRoot
        } else {
            Install-EmbeddedPythonFromZip -Dest $PythonRoot -EmbedZip $EmbedZip -EmbedUrls $EmbedUrls
        }
        Write-PythonPth -Dest $PythonRoot
    } else {
        Write-PythonPth -Dest $PythonRoot
    }
} else {
    Write-Host "-> SkipPythonDownload: ensure python/ has embed layout (python311.zip + python.exe)"
}

if (-not (Test-Path (Join-Path $PythonRoot "python.exe"))) {
    throw "python.exe not found in runtime-bundle. Run bundle without -SkipPythonDownload."
} elseif (-not (Test-Path (Join-Path $PythonRoot "pythonw.exe"))) {
    throw @"
pythonw.exe missing in runtime-bundle/python.
The embed zip must include pythonw.exe (GUI subsystem). Do NOT copy python.exe to pythonw.exe — that still flashes CMD windows.
Re-run bundle without -SkipPythonDownload or restore pythonw.exe from the official Python embed package.
"@
}

function Copy-RuntimeAppLayer {
    Write-Host "-> Copying API layer + config..."
    $ApiDest = Join-Path $AppRoot "brain-memory-ui/api"
    New-Item -ItemType Directory -Force -Path $ApiDest | Out-Null
    Copy-Item -Recurse -Force "$RepoRoot/brain-memory-ui/api/*" $ApiDest
    Copy-Item -Force "$RepoRoot/api/v1_endpoints.py" $ApiDest
    Copy-Item -Force "$RepoRoot/api/ws_routes.py" $ApiDest
    Copy-Item -Force "$RepoRoot/api/health.py" $ApiDest
    Copy-Item -Force "$RepoRoot/api/system_ready.py" $ApiDest
    Copy-Item -Recurse -Force "$RepoRoot/config" (Join-Path $AppRoot "config")
    Write-Host "-> Copying ir_kernel (required by API routes)..."
    Copy-Item -Recurse -Force "$RepoRoot/ir_kernel" (Join-Path $AppRoot "ir_kernel")
    $config = @{
        edition = "personal"
        apiBase = "http://127.0.0.1:8000"
        wsBase = "ws://127.0.0.1:8000"
    } | ConvertTo-Json -Compress
    Set-Content -Path (Join-Path $AppRoot "cnexus-config.json") -Value $config -Encoding UTF8

    Write-Host "-> Staging conflict monitor data templates..."
    $templates = Join-Path $AppRoot "data-templates"
    New-Item -ItemType Directory -Force -Path $templates | Out-Null
    $logTemplate = @'
{"event":"BUNDLE_TEMPLATE","level":"info","source":"bundle","message":"Runtime conflict monitor log — JSONL one event per line","log_role":"runtime-conflict-monitor","path_hint":"%LOCALAPPDATA%\CNexus\data\runtime-conflict-monitor.log","api_tail":"GET /v1/system/conflict_log?tail=200"}
'@
    Set-Content -Path (Join-Path $templates "runtime-conflict-monitor.log") -Value $logTemplate.TrimEnd() -Encoding UTF8 -NoNewline
    Add-Content -Path (Join-Path $templates "runtime-conflict-monitor.log") -Value "" -Encoding UTF8
    @"
CNexus Runtime 冲突监控日志
==========================

文件（安装后）:
  %LOCALAPPDATA%\CNexus\data\runtime-conflict-monitor.log

格式: JSONL（每行一条 JSON）

在线查看:
  curl http://127.0.0.1:8000/v1/system/conflict_log?tail=200

PowerShell:
  Get-Content "`$env:LOCALAPPDATA\CNexus\data\runtime-conflict-monitor.log" -Tail 50
"@ | Set-Content -Path (Join-Path $templates "runtime-conflict-monitor.README.txt") -Encoding UTF8
}

Copy-RuntimeAppLayer

$proxyEnabled = (Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyEnable -ErrorAction SilentlyContinue).ProxyEnable
if ($proxyEnabled -eq 1) {
    $proxyServer = (Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -Name ProxyServer -ErrorAction SilentlyContinue).ProxyServer
    Write-Host "-> Windows system proxy is on ($proxyServer); pip will bypass it for this script."
}

Write-Host "-> Building wheel (cnexus-runtime-core)..."
Push-Location $RepoRoot
Invoke-PipDirect -PipArgs @('wheel', '.', '--no-deps', '-w', $WheelDir) | Out-Host
$Wheel = Get-ChildItem "$WheelDir/*.whl" | Select-Object -First 1
if (-not $Wheel) { throw "Wheel build failed" }

Write-Host "-> Installing runtime dependencies to site-packages..."
$pipInstallArgs = @('install')
if ($refreshDeps) { $pipInstallArgs += '--upgrade' }
$pipInstallArgs += @('-r', 'requirements.txt', '-r', 'brain-memory-ui/api/requirements.txt', '--target', $SitePackages)
Invoke-PipDirect -PipArgs $pipInstallArgs | Out-Host
$wheelInstallArgs = @('install', '--no-deps', $Wheel.FullName, '--target', $SitePackages)
if ($refreshDeps) { $wheelInstallArgs = @('install', '--no-deps', '--upgrade', $Wheel.FullName, '--target', $SitePackages) }
Invoke-PipDirect -PipArgs $wheelInstallArgs | Out-Host
if (Test-Path "$SitePackages/api") {
    Remove-Item "$SitePackages/api" -Recurse -Force
}
Pop-Location

& (Join-Path $ScriptDir "verify-runtime-bundle.ps1")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== Done. runtime-bundle ready for tauri build =="
