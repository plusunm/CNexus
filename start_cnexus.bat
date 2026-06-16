@echo off
:: CNexus 启动器
:: 如果双击无效，请双击项目目录下的 launch.py
chcp 65001 >nul
title CNexus Runtime

cd /d "%~dp0"

echo ========================================
echo   CNexus — Observational Cognition Platform
echo ========================================
echo.

python launch.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo 如果启动失败，请打开终端运行：
    echo   cd /d "D:\类脑记忆\CNexus — Observational Cognition Platform"
    echo   python launch.py
    pause
)
