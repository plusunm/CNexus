# CNexus UI Headless Smoke — Tauri lifecycle probe (requires built CNexus.exe)
param(
    [int]$TimeoutSec = 90,
    [string]$ExePath = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$Frontend = Join-Path $Root "brain-memory-ui\frontend"
$TauriDir = Join-Path $Frontend "src-tauri"
$ReportDir = Join-Path $Root "packaging\prebuild-rc"
$ReportPath = Join-Path $ReportDir "LATEST_UI_SMOKE.txt"
$PassMarker = Join-Path $ReportDir "UI_SMOKE_PASS.json"
$SmokeReport = Join-Path $env:LOCALAPPDATA "CNexus\data\ui-smoke-report.json"

$fail = 0
$pass = 0
$warn = 0
$lines = New-Object System.Collections.Generic.List[string]
$metrics = @{}

function Add-Line($s) { $lines.Add($s) | Out-Null }
function Pass($msg) { $script:pass++; Add-Line "[PASS] $msg"; Write-Host "[PASS] $msg" -ForegroundColor Green }
function Warn($msg) { $script:warn++; Add-Line "[WARN] $msg"; Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail($msg) { $script:fail++; Add-Line "[FAIL] $msg"; Write-Host "[FAIL] $msg" -ForegroundColor Red }

function Stop-AllCnexus {
    $kill = Join-Path $ScriptDir "kill-cnexus-runtime.ps1"
    if (Test-Path $kill) { & powershell -NoProfile -ExecutionPolicy Bypass -File $kill | Out-Null }
    Get-CnexusProcesses | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}

function Sync-BundleApi {
    $apiDest = Join-Path $TauriDir "runtime-bundle\app\brain-memory-ui\api"
    if (-not (Test-Path $apiDest)) { return $false }
    Copy-Item -Force (Join-Path $Root "brain-memory-ui\api\main.py") (Join-Path $apiDest "main.py")
    foreach ($f in @("system_ready.py", "v1_endpoints.py", "health.py", "ws_routes.py")) {
        $src = Join-Path $Root "api\$f"
        if (Test-Path $src) { Copy-Item -Force $src (Join-Path $apiDest $f) }
    }
    return $true
}

function Find-CnexusExe {
    param([string]$Override)
    if ($Override -and (Test-Path $Override)) { return (Resolve-Path $Override).Path }
    $candidates = @(
        (Join-Path $TauriDir "target\release\cnexus-product.exe"),
        (Join-Path $TauriDir "target\release\CNexus.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\CNexus\CNexus.exe"),
        (Join-Path $env:LOCALAPPDATA "CNexus\CNexus.exe")
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return (Resolve-Path $c).Path }
    }
    return $null
}

function Get-FloatWindowInfo {
    Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public class CnexusWin {
  public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc lpEnumFunc, IntPtr lParam);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
  public static string Found = "";
  public static bool Callback(IntPtr hWnd, IntPtr lParam) {
    var sb = new StringBuilder(256);
    GetWindowText(hWnd, sb, 256);
    string title = sb.ToString();
    if (title -eq "CNexus" -and IsWindowVisible(hWnd)) {
      RECT r; GetWindowRect(hWnd, out r);
      int w = r.Right - r.Left; int h = r.Bottom - r.Top;
      if (w -ge 200 -and h -ge 100) { Found = w.ToString() + "x" + h.ToString(); return false; }
    }
    return true;
  }
  public static string Find() {
    Found = ""; EnumWindows(Callback, IntPtr.Zero); return Found;
  }
}
"@ -ErrorAction SilentlyContinue | Out-Null
    try { return [CnexusWin]::Find() } catch { return "" }
}

function Get-CnexusProcesses {
    $names = @("CNexus", "cnexus-product")
    $all = @()
    foreach ($n in $names) {
        $all += @(Get-Process -Name $n -ErrorAction SilentlyContinue)
    }
    return $all
}

function Test-WsStateHandshake {
    param([int]$TimeoutMs = 3000)
    $ws = [System.Net.WebSockets.ClientWebSocket]::new()
    $uri = [Uri]"ws://127.0.0.1:8000/ws/state"
    $cts = [System.Threading.CancellationTokenSource]::new()
    $cts.CancelAfter($TimeoutMs)
    try {
        $ws.ConnectAsync($uri, $cts.Token).GetAwaiter().GetResult() | Out-Null
        $buffer = New-Object byte[] 16384
        $segment = [ArraySegment[byte]]::new($buffer)
        $result = $ws.ReceiveAsync($segment, $cts.Token).GetAwaiter().GetResult()
        $text = [Text.Encoding]::UTF8.GetString($buffer, 0, $result.Count)
        return ($text -match "mind_overview")
    } catch {
        return $false
    } finally {
        try { $ws.Dispose() } catch { }
    }
}

function Test-PortListening($port) {
    return $null -ne (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CNexus UI HEADLESS SMOKE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Add-Line "CNexus UI HEADLESS SMOKE"
Add-Line "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Add-Line ""

Add-Line "== Preflight =="
$cnexusExe = Find-CnexusExe -Override $ExePath
if (-not $cnexusExe) {
    Fail "CNexus.exe not found — build first: VS Native Tools -> npm run tauri:build"
    Fail "  or pass -ExePath to installed CNexus.exe"
} else {
    Pass "CNexus.exe: $cnexusExe"
}

$sidecar = Join-Path $TauriDir "cnexus-runtime-x86_64-pc-windows-msvc.exe"
if (Test-Path $sidecar) { Pass "sidecar present (dev bundle)" } else { Warn "sidecar not beside tauri dir — installed layout must include cnexus-runtime" }

if (Sync-BundleApi) { Pass "synced api into runtime-bundle" } else { Warn "runtime-bundle missing — use release/install layout with bundle" }

Stop-AllCnexus
Pass "cleared CNexus + runtime before UI smoke"

$dataRoot = Join-Path $env:LOCALAPPDATA "CNexus\data"
New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
if (Test-Path $SmokeReport) { Remove-Item $SmokeReport -Force }
Pass "ui-smoke report path ready: $SmokeReport"

if (-not $cnexusExe) {
    Add-Line ""
    Add-Line "UI SMOKE SUMMARY: PASS=$pass WARN=$warn FAIL=$fail"
    if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null }
    $lines | Set-Content -Path $ReportPath -Encoding UTF8
    exit 1
}

Add-Line ""
Add-Line "== Single instance lock =="
$instSw = [System.Diagnostics.Stopwatch]::StartNew()
$env:CNEXUS_UI_SMOKE = "0"
$env:CNEXUS_UI_SMOKE_AUTO_EXIT = "0"
$firstInst = Start-Process -FilePath $cnexusExe -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 4
$secondInst = Start-Process -FilePath $cnexusExe -PassThru -WindowStyle Minimized
Start-Sleep -Seconds 3
$procs = Get-CnexusProcesses
$instSw.Stop()
$metrics.single_instance_ms = [int]$instSw.ElapsedMilliseconds
if ($procs.Count -eq 1 -and $procs[0].Id -eq $firstInst.Id) {
    Pass "single instance lock: second launch rejected, first pid=$($firstInst.Id)"
} elseif ($procs.Count -le 1 -and $secondInst.HasExited) {
    Pass "single instance lock: second instance exited ($($instSw.ElapsedMilliseconds)ms)"
} else {
    Fail "single instance lock: $($procs.Count) CNexus processes (p1=$($firstInst.Id) p2=$($secondInst.Id))"
}
Stop-AllCnexus
Start-Sleep -Seconds 2

Add-Line ""
Add-Line "== UI lifecycle =="
$uiProc = $null
$sw = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $env:CNEXUS_UI_SMOKE = "1"
    $env:CNEXUS_UI_SMOKE_AUTO_EXIT = "1"
    $uiProc = Start-Process -FilePath $cnexusExe -PassThru -WindowStyle Minimized
    Pass "spawned CNexus pid=$($uiProc.Id) CNEXUS_UI_SMOKE=1"

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    $bootStateOk = $false
    $floatOk = $false
    $readyOk = $false
    $wsOk = $false
    $winSize = ""
    $metrics.ui_boot_ms = $null
    $metrics.runtime_ready_ms = $null
    $metrics.ws_connected_ms = $null
    $metrics.float_window_ms = $null

    while ((Get-Date) -lt $deadline) {
        if ($uiProc.HasExited) {
            Warn "CNexus exited early code=$($uiProc.ExitCode)"
            break
        }

        if ($null -eq $metrics.ui_boot_ms) {
            $side = Get-Process -Name "cnexus-runtime" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($side) { $metrics.ui_boot_ms = [int]$sw.ElapsedMilliseconds }
        }

        if (Test-Path $SmokeReport) {
            try {
                $rep = Get-Content $SmokeReport -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($rep.boot_state -ge 4) {
                    $bootStateOk = $true
                    if ($null -eq $metrics.float_window_ms) { $metrics.float_window_ms = [int]$sw.ElapsedMilliseconds }
                }
                if ($rep.boot_shell_mounted -eq $true) {
                    if ($null -eq $metrics.ttfv_ms -and $null -ne $rep.ttfv_ms) {
                        $metrics.ttfv_ms = [int]$rep.ttfv_ms
                    }
                }
                if ($rep.float_visible -eq $true) { $floatOk = $true }
                if ($rep.runtime_ready -eq $true) { $readyOk = $true }
            } catch { }
        }

        if (-not $readyOk) {
            try {
                $r = Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/system/ready" -TimeoutSec 2
                if ($r.status -eq "ready") {
                    $readyOk = $true
                    if ($null -eq $metrics.runtime_ready_ms) { $metrics.runtime_ready_ms = [int]$sw.ElapsedMilliseconds }
                }
            } catch { }
        }

        if ($readyOk -and -not $wsOk) {
            if (Test-WsStateHandshake -TimeoutMs 2500) {
                $wsOk = $true
                $metrics.ws_connected_ms = [int]$sw.ElapsedMilliseconds
            }
        }

        $winSize = Get-FloatWindowInfo
        if ($winSize) {
            $floatOk = $true
            if ($null -eq $metrics.float_window_ms) { $metrics.float_window_ms = [int]$sw.ElapsedMilliseconds }
        }

        if ($bootStateOk -and $floatOk -and $readyOk -and $wsOk) { break }
        Start-Sleep -Milliseconds 400
    }

    $metrics.boot_ms = [int]$sw.ElapsedMilliseconds
    if ($readyOk) { Pass "/v1/system/ready during UI boot ($($metrics.runtime_ready_ms)ms)" } else { Fail "runtime not ready during UI smoke" }
    if ($wsOk) { Pass "WS /ws/state connected ($($metrics.ws_connected_ms)ms)" } else { Fail "WS handshake failed during UI smoke" }
    if ($bootStateOk) { Pass "BootStateLock >= FloatWindowShown (ui-smoke-report.json)" } else { Fail "boot_state never reached 4" }
    if ($metrics.ttfv_ms -ne $null -and $metrics.ttfv_ms -le 4000) {
        Pass "BootShell TTFV $($metrics.ttfv_ms)ms (<= 4000ms)"
    } elseif ($metrics.ttfv_ms -ne $null) {
        Warn "BootShell TTFV slow ($($metrics.ttfv_ms)ms)"
    } else {
        Fail "boot_shell_mounted / ttfv_ms missing in ui-smoke-report"
    }
    if ($floatOk) {
        Pass "float window detected ($winSize) at $($metrics.float_window_ms)ms"
    } else {
        Fail "float window not visible / undersized"
    }

    $sidecarProc = Get-Process -Name "cnexus-runtime" -ErrorAction SilentlyContinue
    if ($sidecarProc) { Pass "cnexus-runtime sidecar running pid=$($sidecarProc.Id)" } else { Warn "cnexus-runtime process not seen (may be embedded layout)" }

    $exitWait = (Get-Date).AddSeconds(20)
    while ((Get-Date) -lt $exitWait -and -not $uiProc.HasExited) {
        Start-Sleep -Milliseconds 300
    }
    if ($uiProc.HasExited) {
        Pass "CNexus graceful exit code=$($uiProc.ExitCode)"
        $metrics.exit_ms = [int]$sw.ElapsedMilliseconds
    } else {
        Warn "CNexus still running — sending stop"
        Stop-Process -Id $uiProc.Id -Force -ErrorAction SilentlyContinue
        Stop-AllCnexus
    }

    Start-Sleep -Seconds 2
    if (Test-PortListening 8000) { Fail "port 8000 still listening after UI exit" } else { Pass "port 8000 released after UI exit" }
    $orphan = Get-CnexusProcesses + @(Get-Process -Name "cnexus-runtime" -ErrorAction SilentlyContinue)
    if ($orphan.Count -gt 0) { Fail "orphan processes after UI smoke: $($orphan.Name -join ',')" } else { Pass "no orphan CNexus/runtime after exit" }
}
finally {
    Remove-Item Env:CNEXUS_UI_SMOKE -ErrorAction SilentlyContinue
    Remove-Item Env:CNEXUS_UI_SMOKE_AUTO_EXIT -ErrorAction SilentlyContinue
    if ($uiProc -and -not $uiProc.HasExited) {
        Stop-Process -Id $uiProc.Id -Force -ErrorAction SilentlyContinue
    }
    Stop-AllCnexus
    $sw.Stop()
    $metrics.total_ms = [int]$sw.ElapsedMilliseconds
}

Add-Line ""
Add-Line "metrics: ttfv_ms=$($metrics.ttfv_ms) ui_boot_ms=$($metrics.ui_boot_ms) runtime_ready_ms=$($metrics.runtime_ready_ms) ws_connected_ms=$($metrics.ws_connected_ms) float_window_ms=$($metrics.float_window_ms) exit_ms=$($metrics.exit_ms) single_instance_ms=$($metrics.single_instance_ms) total_ms=$($metrics.total_ms)"
Add-Line "========================================"
Add-Line "UI SMOKE SUMMARY: PASS=$pass WARN=$warn FAIL=$fail"
Add-Line "========================================"

if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null }
$lines | Set-Content -Path $ReportPath -Encoding UTF8

if ($fail -eq 0) {
    @{
        passed = $true
        at = (Get-Date).ToString("o")
        ui_boot_ms = $metrics.ui_boot_ms
        runtime_ready_ms = $metrics.runtime_ready_ms
        ws_connected_ms = $metrics.ws_connected_ms
        float_window_ms = $metrics.float_window_ms
        exit_ms = $metrics.exit_ms
        single_instance_ms = $metrics.single_instance_ms
        total_ms = $metrics.total_ms
        cnexus_exe = $cnexusExe
    } | ConvertTo-Json | Set-Content -Path $PassMarker -Encoding UTF8
    Write-Host ""
    Write-Host "UI SMOKE PASSED" -ForegroundColor Green
    Write-Host "Report: $ReportPath" -ForegroundColor Cyan
    exit 0
}

@{ passed = $false; at = (Get-Date).ToString("o") } | ConvertTo-Json | Set-Content -Path $PassMarker -Encoding UTF8
Write-Host ""
Write-Host "UI SMOKE FAILED" -ForegroundColor Red
Write-Host "Report: $ReportPath" -ForegroundColor Cyan
exit 1
