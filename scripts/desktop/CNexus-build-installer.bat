@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title CNexus Build
cd /d "%~dp0"

echo.
echo  CNexus 安装包构建
echo  ----------------------------------------
echo  预计 8-15 分钟，请勿关闭本窗口
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch-build.ps1"
set "EC=%ERRORLEVEL%"

echo.
if not "%EC%"=="0" (
    echo [ERROR] 构建失败，退出码 %EC%
    echo 详细日志: %LOCALAPPDATA%\CNexus\build-logs\
    echo.
    pause
    exit /b %EC%
)

echo [OK] 构建完成，窗口 5 秒后关闭...
timeout /t 5 >nul
exit /b 0
