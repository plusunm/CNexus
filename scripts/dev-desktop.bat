@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title CNexus Dev

set "MODE=%~1"
if "%MODE%"=="" set "MODE=tauri"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev-desktop.ps1" -Mode %MODE%
set "EC=%ERRORLEVEL%"
if %EC% neq 0 pause
exit /b %EC%
