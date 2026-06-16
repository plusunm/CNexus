@echo off
setlocal EnableExtensions
chcp 65001 >nul 2>&1
title CNexus Build

if /i "%~1"=="quiet" goto :run

echo.
echo  CNexus installer build starting...
echo  Fully automatic. Success = popup + open installer folder.
echo.

:run
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-cnexus-installer.ps1"
set "EC=%ERRORLEVEL%"
if not "%EC%"=="0" (
    echo.
    echo [ERROR] Build failed, exit code %EC%
    pause
)
endlocal & exit /b %EC%
