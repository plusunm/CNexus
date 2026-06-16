# Quick probe for /v1/system/ready diagnostics (dev only)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Sidecar = Join-Path $Root "brain-memory-ui\frontend\src-tauri\cnexus-runtime-x86_64-pc-windows-msvc.exe"
& (Join-Path $Root "scripts\kill-cnexus-runtime.ps1") | Out-Null
$p = Start-Process -FilePath $Sidecar -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 10
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/v1/system/ready" -UseBasicParsing -TimeoutSec 5
    Write-Host "STATUS:" $r.StatusCode
    Write-Host $r.Content
} catch {
    Write-Host "ERR:" $_.Exception.Message
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        Write-Host "BODY:" $reader.ReadToEnd()
    }
}
Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
& (Join-Path $Root "scripts\kill-cnexus-runtime.ps1") | Out-Null
