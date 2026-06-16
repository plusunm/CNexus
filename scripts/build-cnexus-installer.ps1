# CNexus one-click desktop installer build (fully unattended)
# UTF-8 with BOM for Windows PowerShell 5.1
param(
    [switch]$Unattended
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
if ($Host.Name -eq "ConsoleHost") { chcp 65001 | Out-Null }

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Frontend = Join-Path $RepoRoot "brain-memory-ui\frontend"
$Installer = Join-Path $Frontend "src-tauri\target\release\bundle\nsis\CNexus_0.1.0-alpha_x64-setup.exe"
$LogDir = Join-Path $env:LOCALAPPDATA "CNexus\build-logs"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$LogFile = Join-Path $LogDir "build-$Stamp.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $Message"
    Write-Host $line -ForegroundColor $Color
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Show-Notify {
    param(
        [string]$Text,
        [string]$Title,
        [int]$Icon = 64
    )
    if ($Unattended) {
        Write-Log "[notify] $Title — $Text" "Gray"
        return
    }
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($Text, $Title, 0, $Icon) | Out-Null
}

function Invoke-Step {
    param(
        [string]$Label,
        [string]$Command,
        [string]$WorkDir = $RepoRoot
    )
    Write-Log ">>> $Label" "Cyan"
    if ($Label -match 'tauri') {
        Write-Host ""
        Write-Host "  [i] Next + bundle + Rust + NSIS: about 8-15 minutes." -ForegroundColor Yellow
        Write-Host "  [i] NSIS compress (~400MB) can take 3-5 min with little output — still running." -ForegroundColor Yellow
        Write-Host ""
    }

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $stepLog = Join-Path $LogDir "step-$Stamp-$($Label -replace '[^a-zA-Z0-9]','-').log"
    if (Test-Path $stepLog) { Remove-Item $stepLog -Force }

    $tmpCmd = Join-Path $env:TEMP "cnexus-step-$Stamp-$([guid]::NewGuid().ToString('n').Substring(0,8)).cmd"
    $cmdBody = @(
        "@echo off"
        "chcp 65001 >nul 2>&1"
        $Command
        "exit /b %ERRORLEVEL%"
    ) -join "`r`n"
    [System.IO.File]::WriteAllText($tmpCmd, $cmdBody, [System.Text.UTF8Encoding]::new($false))

    $process = Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList "/c", "`"$tmpCmd`"" `
        -WorkingDirectory $WorkDir `
        -Wait -PassThru -NoNewWindow `
        -RedirectStandardOutput $stepLog `
        -RedirectStandardError "${stepLog}.err"
    $code = $process.ExitCode
    if ($null -eq $code) { $code = 1 }
    Remove-Item $tmpCmd -Force -ErrorAction SilentlyContinue

    if (Test-Path $stepLog) {
        Get-Content -Path $stepLog -Encoding UTF8 | ForEach-Object {
            Write-Host $_
            Add-Content -Path $LogFile -Value $_ -Encoding UTF8
        }
    }
    if (Test-Path "${stepLog}.err") {
        Get-Content -Path "${stepLog}.err" -Encoding UTF8 | ForEach-Object {
            Write-Host $_ -ForegroundColor Yellow
            Add-Content -Path $LogFile -Value $_ -Encoding UTF8
        }
        Remove-Item "${stepLog}.err" -Force -ErrorAction SilentlyContinue
    }
    $ErrorActionPreference = $prevEap

    Write-Log ">>> $Label finished (exit $code)" "Gray"
    if ($code -ne 0) {
        Write-Host ""
        Write-Host "  --- last 40 lines of $Label ---" -ForegroundColor Red
        if (Test-Path $stepLog) {
            Get-Content -Path $stepLog -Tail 40 -Encoding UTF8 | ForEach-Object { Write-Host $_ }
        }
        Write-Host "  --- full step log: $stepLog ---" -ForegroundColor Yellow
        Write-Host ""
        $tail = if (Test-Path $stepLog) {
            (Get-Content -Path $stepLog -Tail 8 -Encoding UTF8) -join " | "
        } else { "no step log" }
        throw "$Label failed (exit $code). Last output: $tail"
    }
}

try {
    Write-Log "========================================" "Green"
    Write-Log "  CNexus build installer" "Green"
    Write-Log "  Log: $LogFile" "Gray"
    Write-Log "  ETA 8-15 min, do not close this window" "Gray"
    Write-Log "========================================" "Green"

    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        throw "npm not found. Install Node.js from https://nodejs.org/"
    }

    Write-Log ">>> ensure NSIS (makensis)" "Cyan"
    $ensureNsis = Join-Path $RepoRoot "scripts\ensure-nsis.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $ensureNsis
    if ($LASTEXITCODE -ne 0) {
        throw "NSIS setup failed (exit $LASTEXITCODE)"
    }
    foreach ($candidate in @(
            "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
            "${env:ProgramFiles}\NSIS\makensis.exe"
        )) {
        if (Test-Path $candidate) {
            $nsisDir = Split-Path $candidate -Parent
            if ($env:PATH -notlike "*$nsisDir*") {
                $env:PATH = "$nsisDir;$env:PATH"
            }
            Write-Log "NSIS on PATH: $candidate" "Gray"
            break
        }
    }

    $killBat = Join-Path $RepoRoot "scripts\kill-cnexus-before-build.bat"
    Invoke-Step "kill processes" "`"$killBat`" quiet"

    if (-not (Test-Path $Frontend)) {
        throw "frontend dir not found: $Frontend"
    }
    Set-Location $Frontend

    $needInstall = $false
    $stampFile = ".cnexus-deps-stamp"
    if (-not (Test-Path "node_modules")) {
        $needInstall = $true
        Write-Log "node_modules missing -> npm install"
    }
    elseif (Test-Path "package-lock.json") {
        $lockHash = (Get-FileHash "package-lock.json" -Algorithm SHA256).Hash
        $savedHash = if (Test-Path $stampFile) { Get-Content $stampFile -Raw } else { "" }
        if ($lockHash -ne $savedHash.Trim()) {
            $needInstall = $true
            Write-Log "package-lock.json changed -> npm install"
        }
    }

    if ($needInstall) {
        Invoke-Step "npm install" "npm install --no-fund --no-audit" -WorkDir $Frontend
        if (Test-Path "package-lock.json") {
            $lockHash = (Get-FileHash "package-lock.json" -Algorithm SHA256).Hash
            Set-Content -Path $stampFile -Value $lockHash -Encoding ASCII -NoNewline
        }
    } else {
        Write-Log "deps unchanged, skip npm install" "Gray"
    }

    Write-Log ">>> tauri:build:vs" "Cyan"
    Write-Host ""
    Write-Host "  [i] Next + bundle + Rust + NSIS: about 8-15 minutes." -ForegroundColor Yellow
    Write-Host "  [i] NSIS compress (~400MB) can take 3-5 min with little output — still running." -ForegroundColor Yellow
    Write-Host ""
    $tauriLog = Join-Path $LogDir "step-$Stamp-tauri-build-vs.log"
    Push-Location $Frontend
    try {
        # Do NOT pipe npm — PS pipeline breaks long npm chains and yields false exit -1
        Start-Transcript -Path $tauriLog -Append | Out-Null
        & npm run tauri:build:vs
        $tauriCode = $LASTEXITCODE
    } finally {
        Stop-Transcript | Out-Null
        Pop-Location
    }
    Write-Log ">>> tauri:build:vs finished (exit $tauriCode)" "Gray"
    if ($tauriCode -ne 0) {
        throw "tauri:build:vs failed (exit $tauriCode). Log: $tauriLog"
    }

    $verifyNsis = Join-Path $RepoRoot "scripts\verify-nsis-installer.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $verifyNsis -InstallerPath $Installer
    if ($LASTEXITCODE -ne 0) {
        throw "verify nsis installer failed (exit $LASTEXITCODE)"
    }
    Write-Log ">>> verify nsis installer finished (exit 0)" "Gray"

    Write-Log "========================================" "Green"
    Write-Log "  BUILD OK" "Green"
    Write-Log "========================================" "Green"

    if (Test-Path $Installer) {
        Write-Log "Installer: $Installer" "Green"
        Start-Process explorer.exe -ArgumentList "/select,`"$Installer`""
        Show-Notify -Text "Installer ready. Opened in Explorer.`n`n$Installer" -Title "CNexus OK" -Icon 64
    } else {
        $bundleDir = Join-Path $Frontend "src-tauri\target\release\bundle"
        Start-Process explorer.exe -ArgumentList "`"$bundleDir`""
        Show-Notify -Text "Build OK but default installer path missing. Opened bundle folder." -Title "CNexus OK" -Icon 48
    }

    Write-Log "Closing in 3 seconds..." "Gray"
    Start-Sleep -Seconds 3
    exit 0
}
catch {
    Write-Log "BUILD FAILED: $($_.Exception.Message)" "Red"
    Write-Log "Full log: $LogFile" "Yellow"
    Show-Notify -Text "Build failed.`n`n$($_.Exception.Message)`n`nLog: $LogFile" -Title "CNexus FAILED" -Icon 16
    Start-Process notepad.exe -ArgumentList "`"$LogFile`""
    if ($Unattended) {
        Write-Log "Unattended mode — skipping Enter prompt" "Gray"
    } else {
        Read-Host "Press Enter to close"
    }
    exit 1
}
