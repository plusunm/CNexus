# Generate human-readable RC signoff digest (SIGNOFF_SUMMARY.md)
param(
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$ReportDir = Join-Path $Root "packaging\prebuild-rc"
$SignoffPath = Join-Path $ReportDir "MANUAL_SIGNOFF.json"
$SmokePath = Join-Path $ReportDir "SMOKE_PASS.json"
$UiSmokePath = Join-Path $ReportDir "UI_SMOKE_PASS.json"
$GatePath = Join-Path $ReportDir "LATEST_GATE.txt"
$AuditPath = Join-Path $ReportDir "LATEST_AUDIT.txt"
$OutPath = Join-Path $ReportDir "SIGNOFF_SUMMARY.md"
$VersionPath = Join-Path $Root "VERSION"

function Mark-Bool($v) {
    if ($v -eq $true) { return "PASS" }
    if ($v -eq $false) { return "FAIL" }
    return "N/A"
}

function Mark-Gate($v) {
    if ($v -eq $true) { return "yes" }
    if ($v -eq $false) { return "no" }
    return "pending"
}

function Icon-Gate($v) {
    switch (Mark-Gate $v) {
        "yes" { return "PASS" }
        "no" { return "FAIL" }
        default { return "PENDING" }
    }
}

$version = "0.1.0-alpha"
if (Test-Path $VersionPath) {
    $version = (Get-Content $VersionPath -Raw).Trim()
}

$sign = $null
if (Test-Path $SignoffPath) {
    $sign = Get-Content $SignoffPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($sign.release.version) { $version = $sign.release.version }
}

$smoke = $null
if (Test-Path $SmokePath) {
    $smoke = Get-Content $SmokePath -Raw -Encoding UTF8 | ConvertFrom-Json
}

$gateSummary = ""
$gateBuildAllowed = $null
$gateLastRun = ""
if (Test-Path $GatePath) {
    $gateLines = Get-Content $GatePath -Encoding UTF8
    $gateSummary = [string]($gateLines | Where-Object { $_ -match "^GATE SUMMARY:" } | Select-Object -First 1)
    $gateLastRun = [string](($gateLines | Where-Object { $_ -match "^Time:" } | Select-Object -First 1) -replace "^Time:\s*", "").Trim()
    $buildLine = $gateLines | Where-Object { $_ -match "^BUILD ALLOWED:" } | Select-Object -First 1
    if ($buildLine -match "BUILD ALLOWED:\s*(.+)") {
        $gateBuildAllowed = ($Matches[1].Trim() -eq "YES (automated)")
    }
}

# Prefer signoff-attached smoke if present
$smokePassed = $null
$readyMs = $null
$wsMs = $null
$shutdownMs = $null
$smokeAt = ""
if ($sign -and $sign.automated_attached -and $sign.automated_attached.smoke) {
    $s = $sign.automated_attached.smoke
    $smokePassed = $s.passed
    $readyMs = $s.ready_ms
    $wsMs = $s.ws_ms
    $shutdownMs = $s.shutdown_ms
    $smokeAt = $s.at
}
if ($null -eq $smokePassed -and $smoke) {
    $smokePassed = $smoke.passed
    $readyMs = $smoke.ready_ms
    $wsMs = $smoke.ws_ms
    $shutdownMs = $smoke.shutdown_ms
    $smokeAt = $smoke.at
}

$uiSmoke = $null
$uiSmokePassed = $null
$uiBootMs = $null
if (Test-Path $UiSmokePath) {
    $uiSmoke = Get-Content $UiSmokePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $uiSmokePassed = $uiSmoke.passed
    $uiBootMs = $uiSmoke.boot_ms
}

$signed = $false
$signedBy = ""
$signedAt = ""
$testEnv = ""
if ($sign) {
    if ($sign.signoff) {
        $signed = [bool]$sign.signoff.signed
        $signedBy = [string]$sign.signoff.signed_by
        $signedAt = [string]$sign.signoff.signed_at
        $testEnv = [string]$sign.signoff.test_environment
    } else {
        $signed = [bool]$sign.signed
        $signedBy = [string]$sign.signed_by
        $signedAt = [string]$sign.signed_at
    }
}

$hostname = ""
$dpi = ""
$isAdmin = $null
$osCaption = ""
if ($sign -and $sign.machine_context) {
    $hostname = [string]$sign.machine_context.hostname
    $dpi = [string]$sign.machine_context.dpi_percent
    $isAdmin = $sign.machine_context.user_is_admin
    $osCaption = [string]$sign.machine_context.os_caption
}

$gateLabels = [ordered]@{
    installer_install_ok = "Installer install"
    appdata_paths_ok = "AppData paths writable"
    runtime_auto_start_ok = "Runtime auto-start"
    float_ui_ok_no_mahjong = "Float UI (no mahjong tile)"
    no_cmd_black_window_ok = "No CMD black window"
    tray_quit_no_orphan = "Tray quit (no orphan)"
    uninstall_no_orphan = "Uninstall (no orphan)"
    port_8000_released_after_quit = "Port 8000 released after quit"
}

$optionalLabels = [ordered]@{
    dpi_125_150_ok = "DPI 125% / 150%"
    low_privilege_data_write_ok = "Low-privilege data write"
    registry_clean_after_uninstall_ok = "Registry clean after uninstall"
    alt_shift_m_toggle_ok = "Alt+Shift+M toggle"
    dual_monitor_float_ok = "Dual monitor float"
}

$warnings = New-Object System.Collections.Generic.List[string]

if ($smokePassed -ne $true) { $warnings.Add("smoke_not_passed") }
if ($uiSmokePassed -ne $true) { $warnings.Add("ui_smoke_not_passed_or_not_run") }
if ($null -ne $readyMs -and $readyMs -gt 15000) { $warnings.Add("runtime_ready_slow ($readyMs ms)") }
if ($gateBuildAllowed -eq $false) { $warnings.Add("automated_gate_not_green (link/cl PATH?)") }
if (-not $signed) { $warnings.Add("manual_signoff_not_signed") }

if ($sign -and $sign.optional_gates) {
    foreach ($entry in $optionalLabels.GetEnumerator()) {
        $key = $entry.Key
        $val = $sign.optional_gates.$key
        if ($val -ne $true) {
            $warnings.Add("$key`_not_verified")
        }
    }
}

if ($sign -and $sign.artifacts -and $sign.artifacts.screenshots) {
    foreach ($prop in $sign.artifacts.screenshots.PSObject.Properties) {
        $p = [string]$prop.Value
        if ([string]::IsNullOrWhiteSpace($p)) { continue }
        $abs = Join-Path $Root ($p -replace "/", "\")
        if (-not (Test-Path $abs)) {
            $warnings.Add("artifact_missing: $($prop.Name)")
        }
    }
}

$readiness = "RC Candidate (not approved)"
if ($signed -and $smokePassed -eq $true -and $gateBuildAllowed -eq $true) {
    $readiness = "Release Candidate Approved (automated + signed)"
} elseif ($signed -and $smokePassed -eq $true) {
    $readiness = "RC Signed (gate toolchain may still need VS Native Tools)"
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# CNexus RC Signoff Summary")
$lines.Add("")
$lines.Add("> Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | ``npm run prebuild:rc-report``")
$lines.Add("> Machine JSON: ``packaging/prebuild-rc/MANUAL_SIGNOFF.json``")
$lines.Add("")
$lines.Add("## Release")
$lines.Add("")
$lines.Add("| Field | Value |")
$lines.Add("|-------|-------|")
$lines.Add("| Version | ``$version`` |")
$lines.Add("| Readiness | **$readiness** |")
if ($sign -and $sign.release.setup_exe_path) {
    $lines.Add("| Setup.exe | ``$($sign.release.setup_exe_path)`` |")
}
$lines.Add("")
$lines.Add("## Automated - Smoke (Runtime truth probe)")
$lines.Add("")
$lines.Add("| Metric | Value |")
$lines.Add("|--------|-------|")
$lines.Add("| Smoke | $(Mark-Bool $smokePassed) |")
if ($smokeAt) { $lines.Add("| Smoke at | $smokeAt |") }
if ($null -ne $readyMs) { $lines.Add("| Runtime ready | ${readyMs} ms |") }
if ($null -ne $wsMs) { $lines.Add("| WS first frame | ${wsMs} ms |") }
if ($null -ne $shutdownMs) { $lines.Add("| Shutdown clean | ${shutdownMs} ms |") }
$lines.Add("| Report | [LATEST_SMOKE.txt](./LATEST_SMOKE.txt) |")
$lines.Add("")
$lines.Add("## Automated - UI smoke (Phase 2)")
$lines.Add("")
$lines.Add("| Metric | Value |")
$lines.Add("|--------|-------|")
$lines.Add("| UI smoke | $(Mark-Bool $uiSmokePassed) |")
if ($null -ne $uiBootMs) { $lines.Add("| UI boot to float | ${uiBootMs} ms |") }
$lines.Add("| Report | [LATEST_UI_SMOKE.txt](./LATEST_UI_SMOKE.txt) |")
$lines.Add("")
$lines.Add("## Automated - Gate")
$lines.Add("")
$lines.Add("| Metric | Value |")
$lines.Add("|--------|-------|")
if ($gateLastRun) { $lines.Add("| Last run | $gateLastRun |") }
if ($gateSummary) { $lines.Add("| Summary | $gateSummary |") }
$lines.Add("| Build allowed (automated) | $(Mark-Bool $gateBuildAllowed) |")
$lines.Add("| Report | [LATEST_GATE.txt](./LATEST_GATE.txt), [LATEST_AUDIT.txt](./LATEST_AUDIT.txt) |")
$lines.Add("")
$lines.Add("## Machine context")
$lines.Add("")
$lines.Add("| Field | Value |")
$lines.Add("|-------|-------|")
if ($hostname) { $lines.Add("| Hostname | ``$hostname`` |") }
if ($osCaption) { $lines.Add("| OS | $osCaption |") }
if ($dpi) { $lines.Add("| DPI scale | ${dpi}% |") }
if ($null -ne $isAdmin) {
    $adminLabel = if ($isAdmin) { "yes (admin)" } else { "no (standard user)" }
    $lines.Add("| Admin user | $adminLabel |")
}
if ($testEnv -and $testEnv -notmatch "^e\.g\.") { $lines.Add("| Test environment | $testEnv |") }
$lines.Add("")
$lines.Add("## Manual gates (required)")
$lines.Add("")
if ($sign -and $sign.gates) {
    foreach ($entry in $gateLabels.GetEnumerator()) {
        $key = $entry.Key
        $label = $entry.Value
        $val = $sign.gates.$key
        $note = ""
        if ($sign.gate_notes -and $sign.gate_notes.$key) {
            $note = " - $($sign.gate_notes.$key)"
        }
        $lines.Add("- **$(Icon-Gate $val)** ``$key`` ($label)$note")
    }
} else {
    $lines.Add("_No MANUAL_SIGNOFF.json - run ``npm run prebuild:signoff:draft``_")
}
$lines.Add("")
$lines.Add("## Optional gates")
$lines.Add("")
if ($sign -and $sign.optional_gates) {
    foreach ($entry in $optionalLabels.GetEnumerator()) {
        $key = $entry.Key
        $label = $entry.Value
        $val = $sign.optional_gates.$key
        $lines.Add("- **$(Icon-Gate $val)** ``$key`` ($label)")
    }
} else {
    $lines.Add("_None recorded_")
}
$lines.Add("")
$lines.Add("## Signoff")
$lines.Add("")
$lines.Add("| Field | Value |")
$lines.Add("|-------|-------|")
$lines.Add("| Signed | $(Mark-Bool $signed) |")
if ($signedBy) { $lines.Add("| Signed by | $signedBy |") }
if ($signedAt) { $lines.Add("| Signed at | $signedAt |") }
if ($sign -and $sign.artifacts.root_dir) {
    $lines.Add("| Artifacts | ``$($sign.artifacts.root_dir)`` |")
}
$lines.Add("")
$lines.Add("## Warnings")
$lines.Add("")
if ($warnings.Count -eq 0) {
    $lines.Add("_None_")
} else {
    foreach ($w in $warnings) { $lines.Add("- ``$w``") }
}
$lines.Add("")
$lines.Add("## Evidence chain")
$lines.Add("")
$lines.Add('```text')
$lines.Add('Source -> Static Gate -> Smoke Runtime -> MANUAL_SIGNOFF -> gate:strict -> tauri:build')
$lines.Add('```')
$lines.Add("")
$lines.Add("## Next steps")
$lines.Add("")
if ($gateBuildAllowed -ne $true) {
    $lines.Add("1. Open **VS x64 Native Tools** -> ``npm run prebuild:gate`` (link/cl on PATH)")
}
if ($smokePassed -ne $true) {
    $lines.Add("- Run ``npm run prebuild:smoke``")
}
if (-not $signed) {
    $lines.Add("- Complete [MANUAL_VERIFICATION.md](./MANUAL_VERIFICATION.md) -> set ``signoff.signed=true``")
}
if ($signed -and $smokePassed -eq $true -and $gateBuildAllowed -eq $true) {
    $lines.Add("- Run ``npm run prebuild:gate:strict`` -> then ``npm run tauri:build``")
} elseif ($signed) {
    $lines.Add("- Run ``npm run prebuild:gate:strict`` when gate + smoke green")
}
$lines.Add("- Phase 2: ``npm run prebuild:smoke:ui`` after ``tauri:build`` (requires CNexus.exe)")
$lines.Add("")

$lines | Set-Content -Path $OutPath -Encoding UTF8

if (-not $Quiet) {
    Write-Host ""
    Write-Host "RC report written:" -ForegroundColor Green
    Write-Host "  $OutPath"
    Write-Host ""
    Write-Host "Readiness: $readiness" -ForegroundColor Cyan
    if ($warnings.Count -gt 0) {
        Write-Host "Warnings: $($warnings.Count)" -ForegroundColor Yellow
    }
}
