# Repo-local launcher (no hardcoded path)
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Script = Join-Path $RepoRoot "scripts\build-cnexus-installer.ps1"
if (-not (Test-Path $Script)) { throw "Missing: $Script" }
& $Script
exit $LASTEXITCODE
