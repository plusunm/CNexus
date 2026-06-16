# Run a command inside VS x64 Native Tools environment (reproducible CI-style)
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Command
)

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot

foreach ($candidate in @(
        "${env:ProgramFiles(x86)}\NSIS\makensis.exe"
        "${env:ProgramFiles}\NSIS\makensis.exe"
    )) {
    if (Test-Path $candidate) {
        $nsisDir = Split-Path $candidate -Parent
        if ($env:PATH -notlike "*$nsisDir*") {
            $env:PATH = "$nsisDir;$env:PATH"
        }
        break
    }
}

function Find-VcVars64 {
    $roots = @(
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"),
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"),
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat")
    )
    foreach ($c in $roots) {
        if (Test-Path $c) { return (Resolve-Path $c).Path }
    }
    $vsRoot = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio"
    $found = Get-ChildItem -LiteralPath $vsRoot -Recurse -Filter "vcvars64.bat" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -match "\\VC\\Auxiliary\\Build\\vcvars64\.bat$" } |
        Select-Object -First 1
    if ($found) { return $found.FullName }
    return $null
}

$vcvars = Find-VcVars64
if (-not $vcvars) {
    Write-Host "FAIL: vcvars64.bat not found" -ForegroundColor Red
    exit 1
}

Write-Host "Running in VS Native context:" -ForegroundColor Cyan
Write-Host "  $Command" -ForegroundColor Gray
Write-Host ""

$wrapped = "call `"$vcvars`" >nul && $Command"
cmd /c $wrapped
exit $LASTEXITCODE
