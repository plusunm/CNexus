# Prepare MANUAL_SIGNOFF.json draft — attach Smoke/Gate metrics + machine context
param(
    [switch]$Force,
    [string]$Version = "0.1.0-alpha"
)

$ErrorActionPreference = "Stop"
Write-Host "prepare-manual-signoff: start" -ForegroundColor Cyan

$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$ReportDir = Join-Path $Root "packaging\prebuild-rc"
$TemplatePath = Join-Path $ReportDir "MANUAL_SIGNOFF.template.json"
$OutPath = Join-Path $ReportDir "MANUAL_SIGNOFF.json"
$SmokePath = Join-Path $ReportDir "SMOKE_PASS.json"
$GatePath = Join-Path $ReportDir "LATEST_GATE.txt"

if (-not (Test-Path $TemplatePath)) { throw "Template missing: $TemplatePath" }
if ((Test-Path $OutPath) -and -not $Force) {
    Write-Host "MANUAL_SIGNOFF.json exists — use -Force to regenerate" -ForegroundColor Yellow
    exit 0
}

$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$artifactRel = "packaging/prebuild-rc/signoff-artifacts/$Version/$stamp"
$artifactAbs = Join-Path $ReportDir "signoff-artifacts\$Version\$stamp"
New-Item -ItemType Directory -Force -Path $artifactAbs | Out-Null

$shotMap = [ordered]@{
    "01_installer_complete" = "01_installer_complete.png"
    "02_float_ui_no_mahjong" = "02_float_ui_no_mahjong.png"
    "03_no_cmd_black_window" = "03_no_cmd_black_window.png"
    "04_dpi_125_float" = "04_dpi_125_float.png"
    "05_dpi_150_float" = "05_dpi_150_float.png"
    "06_tray_quit_task_manager_empty" = "06_tray_quit_task_manager_empty.png"
    "07_port_8000_down_after_quit" = "07_port_8000_down_after_quit.png"
    "08_uninstall_no_residual" = "08_uninstall_no_residual.png"
    "09_registry_or_appdata_clean_optional" = "09_registry_or_appdata_clean_optional.png"
}
$screenshots = @{}
foreach ($entry in $shotMap.GetEnumerator()) {
    $rel = "$artifactRel/$($entry.Value)"
    $screenshots[$entry.Key] = $rel
    $touch = Join-Path $artifactAbs $entry.Value
    if (-not (Test-Path $touch)) { New-Item -ItemType File -Path $touch | Out-Null }
}
$readme = Join-Path $artifactAbs "README.txt"
@(
    "CNexus RC signoff artifacts ($Version / $stamp)"
    "See packaging/prebuild-rc/MANUAL_SIGNOFF_GUIDE.md"
) | Set-Content -Path $readme -Encoding UTF8

$smokeAttach = @{
    passed = $null
    at = ""
    ready_ms = $null
    ws_ms = $null
    shutdown_ms = $null
    total_ms = $null
}
if (Test-Path $SmokePath) {
    $smoke = Get-Content $SmokePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $smokeAttach.passed = $smoke.passed
    $smokeAttach.at = $smoke.at
    $smokeAttach.ready_ms = $smoke.ready_ms
    $smokeAttach.ws_ms = $smoke.ws_ms
    if ($null -ne $smoke.shutdown_ms) { $smokeAttach.shutdown_ms = $smoke.shutdown_ms }
    $smokeAttach.total_ms = $smoke.total_ms
}

$gateAttach = @{ last_run_at = ""; summary = ""; build_allowed = $null }
if (Test-Path $GatePath) {
    $gateLines = Get-Content $GatePath -Encoding UTF8
    $timeLine = $gateLines | Where-Object { $_ -match "^Time:" } | Select-Object -First 1
    if ($timeLine) { $gateAttach.last_run_at = ($timeLine -replace "^Time:\s*", "").Trim() }
    $summaryLine = $gateLines | Where-Object { $_ -match "^GATE SUMMARY:" } | Select-Object -First 1
    $gateAttach.summary = if ($summaryLine) { [string]$summaryLine } else { "" }
    $buildLine = $gateLines | Where-Object { $_ -match "^BUILD ALLOWED:" } | Select-Object -First 1
    if ($buildLine -match "BUILD ALLOWED:\s*(.+)") {
        $gateAttach.build_allowed = ($Matches[1].Trim() -eq "YES (automated)")
    }
}

$dpiPercent = "100"
try {
    $logPixels = (Get-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name LogPixels -ErrorAction SilentlyContinue).LogPixels
    if ($logPixels) { $dpiPercent = [string]([math]::Round($logPixels / 96.0 * 100)) }
} catch { }

$isAdmin = $false
try {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
} catch { }

$doc = [ordered]@{
    schema_version = "1.1"
    _instructions = "Complete manual checks; set gates.* true; signoff.signed=true for prebuild:gate:strict."
    release = [ordered]@{
        version = $Version
        setup_exe_path = ""
        setup_exe_sha256 = ""
        build_host = $env:COMPUTERNAME
    }
    signoff = [ordered]@{
        signed = $false
        signed_by = ""
        signed_at = ""
        test_environment = "e.g. Win11 23H2 clean VM, DPI 125%, standard user"
    }
    automated_attached = [ordered]@{
        generated_at = (Get-Date).ToString("o")
        generator = "scripts/prepare-manual-signoff.ps1"
        smoke_pass_json = "packaging/prebuild-rc/SMOKE_PASS.json"
        gate_report = "packaging/prebuild-rc/LATEST_GATE.txt"
        audit_report = "packaging/prebuild-rc/LATEST_AUDIT.txt"
        smoke = $smokeAttach
        gate = $gateAttach
    }
    machine_context = [ordered]@{
        hostname = $env:COMPUTERNAME
        os_caption = [System.Environment]::OSVersion.VersionString
        os_version = [System.Environment]::OSVersion.Version.ToString()
        dpi_percent = $dpiPercent
        user_is_admin = $isAdmin
        install_root = (Join-Path $env:LOCALAPPDATA "CNexus")
        data_dir = (Join-Path $env:LOCALAPPDATA "CNexus\data")
    }
    artifacts = [ordered]@{
        root_dir = "$artifactRel/"
        screenshots = $screenshots
        logs = [ordered]@{
            runtime_log_excerpt = ""
            kill_cnexus_runtime_output = ""
            prebuild_smoke_report = "packaging/prebuild-rc/LATEST_SMOKE.txt"
        }
        paths_verified = [ordered]@{
            appdata_data_writable = ""
            installed_cnexus_exe = ""
            installed_sidecar = ""
            runtime_bundle_main_py = ""
        }
    }
    gates = [ordered]@{
        installer_install_ok = $false
        appdata_paths_ok = $false
        runtime_auto_start_ok = $false
        float_ui_ok_no_mahjong = $false
        no_cmd_black_window_ok = $false
        tray_quit_no_orphan = $false
        uninstall_no_orphan = $false
        port_8000_released_after_quit = $false
    }
    optional_gates = [ordered]@{
        dpi_125_150_ok = $false
        low_privilege_data_write_ok = $false
        registry_clean_after_uninstall_ok = $false
        alt_shift_m_toggle_ok = $false
        dual_monitor_float_ok = $false
    }
    gate_notes = [ordered]@{
        installer_install_ok = ""
        float_ui_ok_no_mahjong = ""
        tray_quit_no_orphan = ""
        uninstall_no_orphan = ""
        port_8000_released_after_quit = ""
    }
}

$doc | ConvertTo-Json -Depth 8 | Set-Content -Path $OutPath -Encoding UTF8

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ScriptDir "prebuild-rc-report.ps1") -Quiet | Out-Null

Write-Host ""
Write-Host "MANUAL_SIGNOFF draft ready:" -ForegroundColor Green
Write-Host "  JSON:      $OutPath"
Write-Host "  Artifacts: $artifactAbs"
Write-Host ""
Write-Host "Next: MANUAL_VERIFICATION.md -> gates.* -> signoff.signed -> prebuild:gate:strict" -ForegroundColor Cyan
if (-not (Test-Path $SmokePath)) {
    Write-Host "WARN: run npm run prebuild:smoke first" -ForegroundColor Yellow
}
