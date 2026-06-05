@echo off
chcp 65001 >nul
title Brain-Memory v4.0 Demo (录屏用)
set OLLAMA_MODELS=D:\ollama_models
set LLM_MODEL=llama3.2:3b
set BRAIN_MEMORY_QUIET=1

echo.
echo ========================================
echo  Brain-Memory v4.0 演示 — 录屏前请先:
echo  1. Win+G 打开游戏栏, 或 Win+Alt+R 开始录制
echo  2. 本窗口字体放大 Ctrl+滚轮 便于观看
echo  3. 录制开始后按任意键运行演示 (~60-90s)
echo ========================================
echo.

curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
  echo [启动 Ollama...]
  start "" /min ollama serve
  timeout /t 5 /nobreak >nul
)

cd /d "%~dp0.."
python scripts\demo_text.py
echo.
echo 演示结束 — 按 Win+Alt+R 停止录屏
pause
