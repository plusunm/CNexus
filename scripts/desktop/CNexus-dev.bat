@echo off
setlocal EnableExtensions
title CNexus Dev
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launch-dev.ps1"
set EC=%ERRORLEVEL%
if not %EC%==0 pause
exit /b %EC%
