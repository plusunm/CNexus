@echo off
chcp 65001 >nul 2>&1
pushd "%~dp0"
if errorlevel 1 (
    echo ❌ 无法进入项目目录
    pause
    exit /b 1
)

title CNexus 2.0 - 统一网关

echo ════════════════════════════════════════
echo   🚀 CNexus 2.0 - 拉起后端 打开前端
echo ════════════════════════════════════════

rem ── 1. 检查端口，有残留则杀 ──
echo [1/3] 检查端口 7864...
netstat -ano | findstr ":7864.*LISTENING" >nul 2>&1
if errorlevel 0 (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7864.*LISTENING"') do (
        taskkill /f /pid %%a >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
)

rem ── 2. 启动后端（独立窗口）──
echo [2/3] 启动 Unified Gateway...
start "CNexus 2.0 - Gateway" /min python -B -u app_v2.py

rem ── 3. 等待就绪 ──
echo [3/3] 等待服务就绪...
setlocal enabledelayedexpansion
set WAIT_MAX=30
set WAIT_COUNT=0

:WAIT_LOOP
timeout /t 1 /nobreak >nul
set /a WAIT_COUNT+=1
netstat -ano | findstr ":7864.*LISTENING" >nul 2>&1
if !errorlevel! neq 0 (
    if !WAIT_COUNT! lss !WAIT_MAX! goto WAIT_LOOP
    echo.
    echo ❌ 服务启动超时（超过%WAIT_MAX%秒）
    echo   请检查 gateway.log 或手动运行 python app_v2.py 看报错
    pause
    exit /b 1
)

rem ── 4. 成功：打开浏览器 ──
echo.
echo ════════════════════════════════════════
echo   ✅ 启动成功！
echo.
echo   后端:  http://127.0.0.1:7864
echo   状态:  http://127.0.0.1:7864/api/status
echo.
echo   ⚡ 后端运行在独立窗口，关闭即可停止服务
echo ════════════════════════════════════════

start http://127.0.0.1:7864

rem ── 5. 保持窗口，直到用户手动关闭或后端退出 ──
echo.
echo   按 0 停止服务并退出
echo   按 1 重新打开前端
echo   按其他键退出（服务后台继续运行）
echo.

:MONITOR_LOOP
netstat -ano | findstr ":7864.*LISTENING" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️  后端服务已停止，按任意键退出
    pause >nul 2>&1
    exit /b 0
)

choice /c 01 /n /t 5 /d 2 >nul 2>&1
if errorlevel 2 goto MONITOR_LOOP
if errorlevel 1 (
    start http://127.0.0.1:7864
    goto MONITOR_LOOP
)
if errorlevel 0 (
    echo.
    echo 🔴 正在停止服务...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":7864.*LISTENING"') do (
        taskkill /f /pid %%a >nul 2>&1
    )
    echo ✅ 服务已停止
    timeout /t 1 /nobreak >nul
    exit /b 0
)

goto MONITOR_LOOP
