# ClawHub 一键发布脚本
# 前置：先完成 CLI 登录
$ErrorActionPreference = "Stop"
$env:PATH = "C:\Program Files\nodejs;" + $env:PATH
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== ClawHub publish: brain-memory v4.0.0 ===" -ForegroundColor Cyan

# 验证登录
clawhub whoami
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n请先登录: clawhub login --token <你的token>`n" -ForegroundColor Yellow
    exit 1
}

# 打包
if (-not (Test-Path "dist\brain-memory-4.0.0.tgz")) {
    npm pack --json --ignore-scripts --pack-destination dist | Out-Null
    Write-Host "[OK] packed dist\brain-memory-4.0.0.tgz"
}

$commit = git rev-parse HEAD
$displayName = "Brain-Memory v4.0"
$changelog = "v4.0.0: episodic+semantic+procedural + HyDE + reconsolidation + Hebbian + prefrontal cache + Ebbinghaus forget + OpenClaw native bridge"

# 发布 (一行写完避免反引号续行问题)
clawhub package publish "dist\brain-memory-4.0.0.tgz" --family code-plugin --name brain-memory --display-name $displayName --version 4.0.0 --source-repo "Boss/brain-memory" --source-commit $commit --changelog $changelog --tags "latest,BrainMemory,openclaw,memory,hebbian,reconsolidation" --no-input

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== 发布成功! ===" -ForegroundColor Green
} else {
    exit $LASTEXITCODE
}
