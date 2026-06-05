@echo off
chcp 65001 >nul 2>&1
title Brain-Memory v3.0 安装
cd /d "%~dp0.."

echo.
echo  ========================================
echo    Brain-Memory v3.0 依赖安装
echo  ========================================
echo.

if defined OLLAMA_MODELS (
  echo OLLAMA_MODELS=%OLLAMA_MODELS%
) else (
  echo 提示: 若 Ollama 模型路径有中文用户名问题，请先 set OLLAMA_MODELS=D:\ollama_models
)

python --version >nul 2>&1
if errorlevel 1 (
  echo [FAIL] 未找到 Python，请安装 Python 3.11+
  pause
  exit /b 1
)

echo [1/3] pip install -r requirements.txt
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo [FAIL] pip 安装失败
  pause
  exit /b 1
)

echo.
echo [2/3] 检查 Ollama 模型（需 ollama 在 PATH 且 serve 运行中）
where ollama >nul 2>&1
if not errorlevel 1 (
  ollama pull nomic-embed-text
  ollama pull llama3.2
) else (
  echo [!!] 跳过 ollama pull — 未找到 ollama 命令
)

echo.
echo [3/3] 冒烟测试 (scheduler 关闭)
python -c "from config_loader import load_plugin_config; from memory_backend import BrainMemoryBackend; c=load_plugin_config(); c['scheduler_enabled']=False; b=BrainMemoryBackend(c); print(b.get_stats())"
if errorlevel 1 (
  echo [FAIL] 后端加载失败
  pause
  exit /b 1
)

echo.
echo [OK] Brain-Memory v3.0 安装完成
echo  配置 OpenClaw: plugins.slots.memory = brain-memory
echo.
pause
