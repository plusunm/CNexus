# Repo-local launcher (no hardcoded path)
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Script = Join-Path $RepoRoot "scripts\dev-desktop.ps1"
if (-not (Test-Path $Script)) { throw "Missing: $Script" }
& $Script -Mode tauri
exit $LASTEXITCODE
