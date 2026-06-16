@echo off
:: 项目内副本 — 与桌面 CNexus启动.bat 同步
chcp 65001 >nul
set "DESKTOP_BAT=%USERPROFILE%\Desktop\CNexus启动.bat"
if exist "%DESKTOP_BAT%" (
    call "%DESKTOP_BAT%"
    exit /b %errorlevel%
)
echo 请从桌面运行 CNexus启动.bat，或将本脚本复制到桌面。
pause
