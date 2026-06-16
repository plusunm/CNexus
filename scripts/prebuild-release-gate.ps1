# CNexus Final Release Gate — fail-fast before production build
param(
    [switch]$Strict,
    [switch]$SkipAudit
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$Frontend = Join-Path $Root "brain-memory-ui\frontend"
$TauriDir = Join-Path $Frontend "src-tauri"
$ReportDir = Join-Path $Root "packaging\prebuild-rc"
$ReportPath = Join-Path $ReportDir "LATEST_GATE.txt"
$SignoffPath = Join-Path $ReportDir "MANUAL_SIGNOFF.json"
$SmokePassPath = Join-Path $ReportDir "SMOKE_PASS.json"

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

function Test-ExeInPath($name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if (-not $cmd) { return $null }
    return $cmd.Source
}

function Test-SourceContains($path, $pattern, $label) {
    if (-not (Test-Path $path)) {
        Fail "$label — file missing: $path"
        return $false
    }
    $raw = Get-Content $path -Raw -Encoding UTF8
    if ($raw -match $pattern) {
        Pass $label
        return $true
    }
    Fail "$label — pattern not found in $(Split-Path $path -Leaf)"
    return $false
}

function Get-SignoffMeta($sign) {
    if ($sign.PSObject.Properties.Name -contains "signoff" -and $sign.signoff) {
        return @{
            Signed = [bool]$sign.signoff.signed
            SignedBy = [string]$sign.signoff.signed_by
            SignedAt = [string]$sign.signoff.signed_at
            Gates = $sign.gates
            OptionalGates = $sign.optional_gates
            Artifacts = $sign.artifacts
            Schema = [string]$sign.schema_version
        }
    }
    return @{
        Signed = [bool]$sign.signed
        SignedBy = [string]$sign.signed_by
        SignedAt = [string]$sign.signed_at
        Gates = $sign.gates
        OptionalGates = $null
        Artifacts = $null
        Schema = ""
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host " CNexus FINAL RELEASE GATE" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Add-Line "CNexus FINAL RELEASE GATE"
Add-Line "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Add-Line "Strict: $Strict"
Add-Line ""

# ===== GATE 0: Toolchain readiness =====
Add-Line "== GATE 0: Toolchain readiness (prebuild-toolchain-check) =="
$toolchainScript = Join-Path $ScriptDir "prebuild-toolchain-check.ps1"
& powershell -NoProfile -ExecutionPolicy Bypass -File $toolchainScript -Quiet | Out-Host
if ($LASTEXITCODE -ne 0) {
    Fail "toolchain not ready — run in VS x64 Native Tools (see LATEST_TOOLCHAIN.txt)"
} else {
    Pass "toolchain ready (cl/link/rust/cargo/node/npm/tauri)"
}

# ===== GATE 1: Compile environment (FAIL fast) =====
Add-Line ""
Add-Line "== GATE 1: Compile environment (must PASS to build) =="
foreach ($tool in @("cargo", "rustc")) {
    try {
        $ver = & $tool --version 2>&1 | Select-Object -First 1
        Pass "$tool : $ver"
    } catch {
        Fail "$tool not runnable — open VS x64 Native Tools or run vcvars64.bat"
    }
    $where = Test-ExeInPath $tool
    if ($where) { Pass "where $tool : $where" } else { Fail "where $tool : not found" }
}

$link = Get-Command link -ErrorAction SilentlyContinue
if ($link) {
    Pass "where link : $($link.Source)"
} else {
    $vsRoot = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio"
    $linkHint = Get-ChildItem -LiteralPath $vsRoot -Recurse -Filter link.exe -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "Host[xX]64\\x64\\link\.exe$" } |
        Select-Object -First 1
    if ($linkHint) {
        Fail "link.exe exists but not in PATH: $($linkHint.FullName) — use vcvars64 / Native Tools"
    } else {
        Fail "link.exe not found — install VS Build Tools C++ workload"
    }
}

$cl = Test-ExeInPath "cl"
if ($cl) { Pass "where cl : $cl" } else { Fail "where cl : not found — MSVC required for Rust MSVC toolchain" }

# ===== GATE 2: Boot determinism (static) =====
Add-Line ""
Add-Line "== GATE 2: Boot state lock / startup determinism =="

$bootRs = Join-Path $TauriDir "src\boot_sequence.rs"
$bootStateRs = Join-Path $TauriDir "src\boot_state.rs"
$systemReadyPy = Join-Path $Root "api\system_ready.py"
Test-SourceContains $systemReadyPy "system_ready_payload" "api/system_ready.py"
Test-SourceContains $bootStateRs "UiRenderAllowed" "BootStateLock UiRenderAllowed state"
Test-SourceContains $bootStateRs "FloatWindowShown" "BootStateLock FloatWindowShown state"
Test-SourceContains $bootRs "/v1/system/ready" "Rust polls /v1/system/ready"
Test-SourceContains $bootRs "cnexus:runtime-boot-timeout" "boot timeout does not fake ready"
Test-SourceContains $bootRs "boot state lock" "show_float_window boot state lock"
Test-SourceContains $bootRs "grant_ui_render_command" "grant_ui_render command"

$conf = Get-Content (Join-Path $TauriDir "tauri.conf.json") -Raw | ConvertFrom-Json
$float = $conf.app.windows | Where-Object { $_.label -eq "float" } | Select-Object -First 1
if ($float.visible -eq $false) { Pass "float.visible=false (no create-and-show)" } else { Fail "float.visible must be false" }
if ($float.width -eq 360 -and $float.height -eq 228) { Pass "float 360x228" } else { Fail "float must be 360x228" }

$bootShell = Join-Path $Frontend "components\desktop\BootShellProtocolRoot.tsx"
$tauriTs = Join-Path $Frontend "lib\tauriDesktop.ts"
Test-SourceContains $tauriTs "cnexus:runtime-ready" "tauriDesktop listenRuntimeReady event"
Test-SourceContains $bootShell "listenRuntimeReady" "BootShellProtocolRoot waits runtime-ready"
Test-SourceContains $bootShell "isRuntimeReady" "BootShellProtocolRoot probes system/ready+WS"
Test-SourceContains $bootShell "grantUiRender" "BootShellProtocolRoot grants UI render"
Test-SourceContains $bootShell "listenRuntimeBootTimeout" "BootShellProtocolRoot demo fallback on timeout"

$bridge = Join-Path $Frontend "cnexus-kernel\MindRuntimeBridge.tsx"
Test-SourceContains $bridge "500" "MindRuntimeBridge startup backoff (500ms)"
Test-SourceContains $bridge "60" "MindRuntimeBridge retry attempts"

$sidecar = Join-Path $TauriDir "cnexus-runtime-sidecar\src\main.rs"
Test-SourceContains $sidecar "Stdio::null" "sidecar stdout/stderr null (no CMD)"
Test-SourceContains $sidecar "python/python\.exe" "sidecar prefers python.exe"
Test-SourceContains (Join-Path $TauriDir "src\lib.rs") "tauri_plugin_single_instance" "single instance plugin (double-click guard)"

# ===== GATE 3: Full engineering audit =====
Add-Line ""
Add-Line "== GATE 3: Engineering audit (prebuild-audit-full) =="
if ($SkipAudit) {
    Warn "Skipped prebuild-audit-full (-SkipAudit)"
} else {
    $auditScript = Join-Path $ScriptDir "prebuild-audit-full.ps1"
    & powershell -NoProfile -ExecutionPolicy Bypass -File $auditScript -SkipToolchain | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Fail "prebuild-audit-full failed — fix before build"
    } else {
        Pass "prebuild-audit-full (toolchain skipped; gate 1 is authoritative)"
    }
}

# ===== GATE 4: Installer artifact hint =====
Add-Line ""
Add-Line "== GATE 4: Installer artifact =="
$setupGlob = Join-Path $TauriDir "target\release\bundle\nsis\CNexus_*-setup.exe"
$setups = Get-ChildItem $setupGlob -ErrorAction SilentlyContinue
if ($setups) {
    Warn "Existing Setup.exe found — re-run MANUAL install verification after next build: $($setups[0].Name)"
} else {
    Warn "No Setup.exe yet — GATE 3 manual (install/uninstall) required after first build"
}

# ===== GATE 5: Manual signoff + smoke marker (Strict) =====
Add-Line ""
Add-Line "== GATE 5: Smoke pass marker (strict requires fresh smoke) =="
if (Test-Path $SmokePassPath) {
    try {
        $smoke = Get-Content $SmokePassPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($smoke.passed -eq $true) {
            $at = [datetime]::Parse($smoke.at)
            $ageH = ((Get-Date) - $at).TotalHours
            Pass "SMOKE_PASS.json ready_ms=$($smoke.ready_ms) age=$([math]::Round($ageH,1))h"
            if ($Strict -and $ageH -gt 24) {
                Fail "SMOKE_PASS older than 24h — re-run npm run prebuild:smoke"
            }
        } elseif ($Strict) {
            Fail "SMOKE_PASS.json passed=false — run npm run prebuild:smoke"
        } else {
            Warn "SMOKE_PASS.json passed=false — run prebuild:smoke before build"
        }
    } catch {
        if ($Strict) { Fail "SMOKE_PASS.json invalid" } else { Warn "SMOKE_PASS.json unreadable" }
    }
} else {
    if ($Strict) {
        Fail "SMOKE_PASS.json missing — run npm run prebuild:smoke"
    } else {
        Warn "No SMOKE_PASS.json — static gate alone cannot catch mahjong/race bugs; run prebuild:smoke"
    }
}

Add-Line ""
Add-Line "== GATE 6: Manual install / float / process signoff =="
if (-not (Test-Path $SignoffPath)) {
    if ($Strict) {
        Fail "MANUAL_SIGNOFF.json missing — copy MANUAL_SIGNOFF.template.json and complete manual gates"
    } else {
        Warn "MANUAL_SIGNOFF.json not present — required for prebuild:gate:strict / RC tag"
    }
} else {
    try {
        $sign = Get-Content $SignoffPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $meta = Get-SignoffMeta $sign
        $required = @(
            "installer_install_ok", "appdata_paths_ok", "runtime_auto_start_ok",
            "float_ui_ok_no_mahjong", "no_cmd_black_window_ok", "tray_quit_no_orphan",
            "uninstall_no_orphan", "port_8000_released_after_quit"
        )
        $allTrue = $true
        foreach ($k in $required) {
            if (-not $meta.Gates.$k) { $allTrue = $false; break }
        }
        if ($meta.Schema) {
            Pass "MANUAL_SIGNOFF schema_version=$($meta.Schema)"
        }
        if ($meta.Signed -eq $true -and $allTrue) {
            Pass "MANUAL_SIGNOFF.json signed by $($meta.SignedBy) @ $($meta.SignedAt)"
        } elseif ($Strict) {
            Fail "MANUAL_SIGNOFF.json incomplete or signed=false"
        } else {
            Warn "MANUAL_SIGNOFF.json present but not fully signed — strict mode will fail"
        }

        if ($meta.OptionalGates) {
            $optRecommended = @("dpi_125_150_ok", "low_privilege_data_write_ok")
            foreach ($ok in $optRecommended) {
                if ($meta.OptionalGates.$ok -ne $true) {
                    if ($Strict) {
                        Warn "optional_gate $ok not true — RC quality gap (not blocking)"
                    }
                } else {
                    Pass "optional_gate $ok"
                }
            }
        }

        if ($Strict -and $meta.Signed -eq $true -and $meta.Artifacts -and $meta.Artifacts.screenshots) {
            $coreShots = @("02_float_ui_no_mahjong", "06_tray_quit_task_manager_empty")
            foreach ($sk in $coreShots) {
                $path = $meta.Artifacts.screenshots.$sk
                if ([string]::IsNullOrWhiteSpace($path)) {
                    Warn "artifact screenshot missing path: $sk"
                } elseif (-not (Test-Path (Join-Path $Root ($path -replace "/", "\")))) {
                    Warn "artifact file not found: $path"
                } else {
                    Pass "artifact $sk"
                }
            }
        }
    } catch {
        if ($Strict) { Fail "MANUAL_SIGNOFF.json invalid JSON: $_" } else { Warn "MANUAL_SIGNOFF.json invalid" }
    }
}

Add-Line ""
Add-Line "Manual checklist: packaging/prebuild-rc/FINAL_RELEASE_GATE.md"
Add-Line "Manual steps: packaging/prebuild-rc/MANUAL_VERIFICATION.md"

# ===== Summary =====
Add-Line ""
Add-Line "========================================"
Add-Line "GATE SUMMARY: PASS=$pass WARN=$warn FAIL=$fail"
Add-Line "BUILD ALLOWED: $(if ($fail -eq 0) { 'YES (automated)' } else { 'NO' })"
if ($Strict) {
    Add-Line "RC TAG ALLOWED: $(if ($fail -eq 0) { 'YES if manual signed' } else { 'NO' })"
} else {
    Add-Line "RC TAG ALLOWED: run prebuild:gate:strict after manual signoff"
}
Add-Line "========================================"

if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
}
$lines | Set-Content -Path $ReportPath -Encoding UTF8
Write-Host ""
Write-Host "Report: $ReportPath" -ForegroundColor Cyan

if ($fail -gt 0) {
    Write-Host ""
    Write-Host "RELEASE GATE FAILED — do NOT run tauri:build" -ForegroundColor Red
    exit 1
}

Write-Host ""
if ($warn -gt 0) {
    Write-Host "RELEASE GATE PASSED (automated) with $warn warning(s)" -ForegroundColor Yellow
} else {
    Write-Host "RELEASE GATE PASSED (automated)" -ForegroundColor Green
}

if ($Strict) {
    Write-Host "Strict mode: manual + automated OK — build/release allowed" -ForegroundColor Green
}

Write-Host ""
Write-Host "Next: npm run prebuild:smoke -> MANUAL signoff -> npm run prebuild:gate:strict" -ForegroundColor Cyan
Write-Host "      (only then tauri:build)" -ForegroundColor Cyan
exit 0
