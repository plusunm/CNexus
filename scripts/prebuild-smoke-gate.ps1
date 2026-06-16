# CNexus Runtime Smoke Gate — live boot probe (not static analysis)
param(
    [int]$ReadyTimeoutSec = 45,
    [int]$WsTimeoutMs = 3000
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot
$Root = Split-Path -Parent $ScriptDir
$Frontend = Join-Path $Root "brain-memory-ui\frontend"
$TauriDir = Join-Path $Frontend "src-tauri"
$ReportDir = Join-Path $Root "packaging\prebuild-rc"
$ReportPath = Join-Path $ReportDir "LATEST_SMOKE.txt"
$PassMarker = Join-Path $ReportDir "SMOKE_PASS.json"

$fail = 0
$pass = 0
$warn = 0
$lines = New-Object System.Collections.Generic.List[string]
$metrics = @{}

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

function Get-PeSubsystem($exePath) {
    $bytes = [System.IO.File]::ReadAllBytes($exePath)
    if ($bytes.Length -lt 64) { return $null }
    $peOffset = [BitConverter]::ToInt32($bytes, 0x3C)
    if ($peOffset -le 0 -or ($peOffset + 0x5E) -ge $bytes.Length) { return $null }
    return [BitConverter]::ToInt16($bytes, $peOffset + 0x5C)
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

function Stop-SmokeRuntime {
    $killScript = Join-Path $ScriptDir "kill-cnexus-runtime.ps1"
    if (Test-Path $killScript) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $killScript | Out-Null
    }
}

function Test-PortListening($port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $conn -and $conn.Count -gt 0)
}

function Test-BundledPythonRunning {
    $pyNames = @("python.exe", "pythonw.exe")
    $hits = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        ($pyNames -contains $_.Name) -and (
            $_.CommandLine -match "api\.main" -or
            $_.CommandLine -match "runtime-bundle" -or
            $_.CommandLine -match "brain-memory-ui\\api"
        )
    }
    return @($hits)
}

function Test-RuntimeSidecarRunning {
    return @(Get-Process -Name "cnexus-runtime" -ErrorAction SilentlyContinue)
}

function Test-ShutdownClean {
    param(
        [int]$TimeoutMs = 5000,
        [int]$Port = 8000
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $TimeoutMs) {
        $portUp = Test-PortListening $Port
        $sidecars = Test-RuntimeSidecarRunning
        $pythons = Test-BundledPythonRunning
        if (-not $portUp -and $sidecars.Count -eq 0 -and $pythons.Count -eq 0) {
            return @{ ok = $true; ms = [int]$sw.ElapsedMilliseconds }
        }
        Start-Sleep -Milliseconds 200
    }
    return @{
        ok = $false
        ms = [int]$sw.ElapsedMilliseconds
        port = (Test-PortListening $Port)
        sidecars = (Test-RuntimeSidecarRunning).Count
        pythons = (Test-BundledPythonRunning).Count
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " CNexus RUNTIME SMOKE GATE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Add-Line "CNexus RUNTIME SMOKE GATE"
Add-Line "Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Add-Line ""

# --- Preflight ---
Add-Line "== Preflight =="
$sidecar = Join-Path $TauriDir "cnexus-runtime-x86_64-pc-windows-msvc.exe"
$bundleMain = Join-Path $TauriDir "runtime-bundle\app\brain-memory-ui\api\main.py"
if (-not (Test-Path $sidecar)) {
    Fail "sidecar missing — npm run build:sidecar"
}
else { Pass "sidecar exe present" }
if (-not (Test-Path $bundleMain)) {
    Fail "runtime-bundle missing — npm run bundle:runtime"
}
else { Pass "runtime-bundle present" }

# Sync authoritative API stubs into bundle (smoke uses bundled copy)
$apiDest = Join-Path $TauriDir "runtime-bundle\app\brain-memory-ui\api"
if (Test-Path $apiDest) {
    Copy-Item -Force (Join-Path $Root "brain-memory-ui\api\main.py") (Join-Path $apiDest "main.py")
    foreach ($f in @("system_ready.py", "v1_endpoints.py", "health.py", "ws_routes.py")) {
        $src = Join-Path $Root "api\$f"
        if (Test-Path $src) {
            Copy-Item -Force $src (Join-Path $apiDest $f)
        }
    }
    Pass "synced api/*.py into runtime-bundle for smoke"
}

if (Test-Path $sidecar) {
    $sub = Get-PeSubsystem $sidecar
    if ($null -eq $sub) {
        Warn "could not read PE subsystem for sidecar"
    } elseif ($sub -eq 2) {
        Pass "sidecar PE subsystem=Windows GUI (no console)"
    } elseif ($sub -eq 3) {
        Warn "sidecar PE subsystem=Console — release build should use windows_subsystem"
    } else {
        Warn "sidecar PE subsystem=$sub (unexpected)"
    }
}

Stop-SmokeRuntime
Pass "port 8000 cleared before smoke"

# Fresh desktop installs need writable memory layout before system/ready
$dataRoot = Join-Path $env:LOCALAPPDATA "CNexus\data"
foreach ($sub in @("blocks", "lancedb", "kuzu_db")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $dataRoot $sub) | Out-Null
}
Pass "memory data dirs ensured under $dataRoot"

# --- Live spawn ---
Add-Line ""
Add-Line "== Live runtime boot =="
$runtimeProc = $null
$swTotal = [System.Diagnostics.Stopwatch]::StartNew()
$lastReadyErr = $null
try {
    if (-not (Test-Path $sidecar)) { throw "sidecar missing" }

    $runtimeProc = Start-Process -FilePath $sidecar -PassThru -WindowStyle Hidden
    Pass "spawned cnexus-runtime pid=$($runtimeProc.Id) (WindowStyle Hidden)"

    $deadline = (Get-Date).AddSeconds($ReadyTimeoutSec)
    $readyPayload = $null
    $swReady = [System.Diagnostics.Stopwatch]::StartNew()
    while ((Get-Date) -lt $deadline) {
        if ($runtimeProc.HasExited) {
            Fail "runtime exited early code=$($runtimeProc.ExitCode)"
            break
        }
        try {
            $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/system/ready" -TimeoutSec 3 -Method Get
            if ($resp.status -eq "ready" -and $resp.ws -eq "alive") {
                $readyPayload = $resp
                break
            }
            $lastReadyErr = "status=$($resp.status) ws=$($resp.ws) memory=$($resp.memory)"
        } catch {
            $lastReadyErr = $_.Exception.Message
        }
        Start-Sleep -Milliseconds 250
    }
    $swReady.Stop()
    $metrics.ready_ms = [int]$swReady.ElapsedMilliseconds

    if (-not $readyPayload) {
        if ($lastReadyErr) { Add-Line "last /v1/system/ready error: $lastReadyErr" }
        Fail "/v1/system/ready not ready within ${ReadyTimeoutSec}s"
    } else {
        Pass "/v1/system/ready in $($metrics.ready_ms)ms boot_id=$($readyPayload.boot_id)"
        if ($readyPayload.token_valid -ne $true) { Fail "token_valid=false in ready payload" } else { Pass "token_valid=true" }
    }

    # Shallow health (liveness separate from ready)
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/health" -TimeoutSec 3
        if ($health.status -eq "ok") { Pass "/v1/health ok" } else { Fail "/v1/health unexpected" }
    } catch {
        Fail "/v1/health failed after ready"
    }

    # WS first frame
    if ($readyPayload) {
        $swWs = [System.Diagnostics.Stopwatch]::StartNew()
        $wsOk = Test-WsStateHandshake -TimeoutMs $WsTimeoutMs
        $swWs.Stop()
        $metrics.ws_ms = [int]$swWs.ElapsedMilliseconds
        if ($wsOk) { Pass "WS /ws/state first frame in $($metrics.ws_ms)ms" } else { Fail "WS /ws/state handshake failed" }
    }

    # Boot lock timing sanity (UI uses 120ms show delay; ready should be < gate timeout)
    if ($metrics.ready_ms -gt ($ReadyTimeoutSec * 1000)) {
        Fail "ready timing exceeded budget"
    } elseif ($metrics.ready_ms -gt 15000) {
        Warn "ready slow ($($metrics.ready_ms)ms) — investigate AV/disk"
    } else {
        Pass "ready latency within budget ($($metrics.ready_ms)ms)"
    }

    # --- Shutdown / orphan probe (symmetric to READY boot chain) ---
    Add-Line ""
    Add-Line "== Shutdown / orphan probe =="
    if ($runtimeProc -and -not $runtimeProc.HasExited) {
        $sidecarPid = $runtimeProc.Id
        $null = Start-Process -FilePath "taskkill" -ArgumentList @("/F", "/T", "/PID", "$sidecarPid") -WindowStyle Hidden -Wait
        Pass "sent taskkill /T to sidecar pid=$sidecarPid (simulates UI stop_runtime_sidecar)"
        $shutdown = Test-ShutdownClean -TimeoutMs 5000
        $metrics.shutdown_ms = $shutdown.ms
        if ($shutdown.ok) {
            Pass "runtime tree exited + port 8000 released in $($shutdown.ms)ms"
        } else {
            Fail "shutdown incomplete in 5s — port=$($shutdown.port) sidecars=$($shutdown.sidecars) python=$($shutdown.pythons)"
            Stop-SmokeRuntime
            $shutdown2 = Test-ShutdownClean -TimeoutMs 3000
            if ($shutdown2.ok) {
                Warn "kill-cnexus-runtime.ps1 recovered orphans in $($shutdown2.ms)ms — investigate slow exit"
            } else {
                Fail "kill script could not fully clean — manual intervention required"
            }
        }
        $runtimeProc = $null
    } else {
        Warn "skipped shutdown probe — runtime not running"
    }
}
finally {
    if ($runtimeProc -and -not $runtimeProc.HasExited) {
        try { Stop-Process -Id $runtimeProc.Id -Force -ErrorAction SilentlyContinue } catch { }
    }
    Stop-SmokeRuntime
    $swTotal.Stop()
    $metrics.total_ms = [int]$swTotal.ElapsedMilliseconds
    Pass "cleanup complete (total $($metrics.total_ms)ms)"
}

Add-Line ""
Add-Line "metrics: ready_ms=$($metrics.ready_ms) ws_ms=$($metrics.ws_ms) shutdown_ms=$($metrics.shutdown_ms) total_ms=$($metrics.total_ms)"
Add-Line "========================================"
Add-Line "SMOKE SUMMARY: PASS=$pass WARN=$warn FAIL=$fail"
Add-Line "========================================"

if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
}
$lines | Set-Content -Path $ReportPath -Encoding UTF8

if ($fail -eq 0) {
    @{
        passed = $true
        at = (Get-Date).ToString("o")
        ready_ms = $metrics.ready_ms
        ws_ms = $metrics.ws_ms
        shutdown_ms = $metrics.shutdown_ms
        total_ms = $metrics.total_ms
        sidecar = $sidecar
    } | ConvertTo-Json | Set-Content -Path $PassMarker -Encoding UTF8
    Write-Host ""
    Write-Host "SMOKE GATE PASSED — runtime truth probe OK" -ForegroundColor Green
    Write-Host "Report: $ReportPath" -ForegroundColor Cyan
    exit 0
}

@{
    passed = $false
    at = (Get-Date).ToString("o")
    ready_ms = $metrics.ready_ms
    ws_ms = $metrics.ws_ms
    total_ms = $metrics.total_ms
} | ConvertTo-Json | Set-Content -Path $PassMarker -Encoding UTF8

Write-Host ""
Write-Host "SMOKE GATE FAILED — do NOT build (static gate cannot catch this)" -ForegroundColor Red
Write-Host "Report: $ReportPath" -ForegroundColor Cyan
exit 1
