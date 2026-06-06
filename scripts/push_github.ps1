param(
    [string]$User = "plusunm",
    [string]$Repo = "brain-memory-g1",
    [switch]$CreateRelease
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path ".git")) {
    Write-Error "Not a git repository. Run from project root."
}

$remoteUrl = "https://github.com/$User/$Repo.git"

if (-not (git remote get-url origin 2>$null)) {
    git remote add origin $remoteUrl
    Write-Host "Added remote: $remoteUrl"
} else {
    git remote set-url origin $remoteUrl
    Write-Host "Updated remote: $remoteUrl"
}

Write-Host "Pushing to GitHub..."
git push -u origin main

if ($CreateRelease) {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Warning "gh CLI not found. Upload dist/brain-memory-5.0.0.zip manually on GitHub Releases."
        exit 0
    }
    if (-not (Test-Path "dist/brain-memory-5.0.0.zip")) {
        python scripts/publish.py
    }
    gh release create v5.0.0 dist/brain-memory-5.0.0.zip --title "Brain-Memory v5.0.0" --notes "Initial release of Brain-Memory v5.0 persistent cognitive runtime."
    Write-Host "Release v5.0.0 created."
}

Write-Host "Done."
