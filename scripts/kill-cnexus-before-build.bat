@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1

if "%~1"=="quiet" goto :do_kill

echo.
echo ========================================
echo  CNexus - 关闭占用进程（构建前清理）
echo ========================================
echo.

:do_kill
set "SCRIPT_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%kill-cnexus-runtime.ps1" >nul 2>&1
powershell -NoProfile -Command "Start-Sleep -Seconds 2"

if "%~1"=="quiet" exit /b 0

echo.
echo [OK] 占用进程已清理
echo.
endlocal
