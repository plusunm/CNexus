# CNexus — 上手指南

三份实用路径：**日常使用**、**开发集成**、**部署给他人**。

英文版：[QUICKSTART.md](QUICKSTART.md)

---

## 一、日常使用（3 步）

面向：每天打开系统、看状态、记东西、偶尔聊天。

### 第 1 步：一键启动

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/load_g1.ps1
```

脚本会自动：

- 使用数据目录 `C:\ProgramData\cnexus\data`
- 检测/启动 API（`:8000`）和前端（`:3000`）
- Ollama 不可用时用 hash embedding 回退（记忆仍可用）

浏览器打开：**http://localhost:3000**

### 第 2 步：熟悉四个页面

| 页面 | 地址 | 用途 |
|------|------|------|
| 仪表盘 | `/` | 稳定性、叙事连贯性、身份状态 |
| 记忆 | `/memory` | 手动写入记忆、测试召回 |
| 对话 | `/chat` | 带长期记忆的聊天（需先配模型） |
| 运行日志 | `/logs` | 捕获、召回、聊天等操作记录 |

**常用操作：**

- 在「记忆」页写入目标：`layer=goal`，importance 设 0.8+
- 召回测试：「我们之前做过什么」「CNexus 是什么」
- 在「模型」页配置 Ollama / OpenAI / DeepSeek，再使用「对话」

### 第 3 步：日常维护

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/governance/state
Invoke-RestMethod -Method POST http://127.0.0.1:8000/governance/cycle
```

**注意：** 记忆/召回不依赖 LLM；导入聊天记录时避免与 API 双写同一数据目录。

---

## 二、开发集成（3 步）

面向：Cursor、Python 脚本、其他 Agent 接入同一套「大脑」。

### 第 1 步：统一走 HTTP API

```text
你的程序 / Cursor Agent / 自动化脚本
        ↓  HTTP
http://127.0.0.1:8000
        ↓
BrainMemoryRuntime（单实例）
        ↓
BM_MEMORY_DIR
```

**核心接口：**

```http
POST /memory/capture
GET  /memory/recall?query=
POST /chat
GET  /governance/state
POST /governance/cycle
WS   /ws/state
WS   /logs/ws
```

### 第 2 步：代码示例

**Python：**

```python
import requests
BASE = "http://127.0.0.1:8000"
requests.post(f"{BASE}/memory/capture", json={
    "role": "user", "content": "我的长期目标", "layer": "goal", "importance": 0.9,
})
ctx = requests.get(f"{BASE}/memory/recall", params={"query": "长期目标"}).json()["context"]
```

**导入 Cursor 聊天记录：**

```powershell
python scripts/import_chat_transcript.py "<transcript.jsonl>" --root "<project-root>"
```

---

## 三、部署给他人使用（3 步）

### 第 1 步：环境与数据

| 变量 | 说明 |
|------|------|
| `BM_MEMORY_DIR` | 持久化数据目录 |
| `NEXT_PUBLIC_API_BASE` | 前端连 API 的地址 |
| `BM_CORS_ORIGINS` | 允许的前端来源 |

### 第 2 步：配置模型与安全

- 在 `/models` 配置 LLM，API Key 存 `config/models.local.json`
- 公网部署用 Nginx/Caddy + HTTPS，定期备份 `BM_MEMORY_DIR`

### 第 3 步：多客户端

- ✅ 多客户端读 + 单 API 写
- ❌ 不要多进程同时写同一数据目录

---

## 速查

| 场景 | 入口 |
|------|------|
| 日常打开 | `load_g1.ps1` → http://localhost:3000 |
| 脚本接入 | `POST/GET /memory/*` |
| 导入聊天 | `scripts/import_chat_transcript.py` |
| GitHub | https://github.com/plusunm/CNexus |
