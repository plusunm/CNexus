# CNexus UI

**CNexus 的可视化与交互层** — 与核心 Runtime 解耦，支持 Web / Desktop / Mobile 多端。

## 架构

```text
┌─────────────────────────────────────────────────────────┐
│  brain-memory-ui                                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Next.js  │  │  Tauri   │  │ Flutter  │            │
│  │   Web    │  │ Desktop  │  │  Mobile  │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       └─────────────┼─────────────┘                    │
│                     │ HTTP / WebSocket                │
│              ┌──────▼──────┐                           │
│              │  FastAPI    │  :8000                   │
│              │  Runtime API│                           │
│              └──────┬──────┘                           │
└─────────────────────┼──────────────────────────────────┘
                      │
              ┌───────▼────────┐
              │ CNexus Core    │  (brain_memory/)
              └────────────────┘
```

## 技术栈

| 层面 | 技术 |
|------|------|
| Web | Next.js 15 + TypeScript + Tailwind + Zustand + Recharts |
| API | FastAPI + WebSocket |
| Desktop | Tauri 2.0（待集成，复用 Web 前端） |
| Mobile | Flutter 3.24（待集成，调用同一 API） |

## 快速启动

### 1. 安装核心依赖（仓库根目录）

```bash
cd "D:\类脑记忆\CNexus — Observational Cognition Platform"
pip install -r requirements.txt
pip install -r brain-memory-ui/api/requirements.txt
```

### 2. 启动 Runtime API（端口 8000）

```bash
cd brain-memory-ui
python -m api.main
```

### 3. 启动 Web 前端（端口 3000）

```bash
cd brain-memory-ui/frontend
npm install
npm run dev
```

浏览器打开：**http://localhost:3000**

### 一键启动（Windows）

```powershell
.\brain-memory-ui\scripts\start.ps1
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/memory/capture` | 写入记忆 |
| GET | `/memory/recall?query=` | 召回记忆 |
| POST | `/chat` | 对话（含记忆） |
| GET | `/models` | 模型列表 |
| GET | `/governance/state` | 实时状态 |
| POST | `/governance/cycle` | 稳定性治理 |
| WS | `/ws/state` | 状态流推送（2s） |
| WS | `/ws/chat` | WebSocket 对话 |

## Agent 集成

Agent 只需调用 Runtime API，无需嵌入 UI：

```python
import httpx
ctx = httpx.get("http://localhost:8000/memory/recall", params={"query": "用户目标"}).json()
# 注入 LLM → 回复后 POST /memory/capture
```

## 目录

```text
brain-memory-ui/
├── api/           # FastAPI Runtime API
├── frontend/      # Next.js Web
├── desktop/       # Tauri（ scaffold ）
├── mobile/        # Flutter（ scaffold ）
├── shared/        # 共享类型
├── scripts/       # 启动脚本
└── docs/
```

## 与旧版 web/ 的关系

- `web/` — 轻量单页 UI（FastAPI 静态，:8080）
- `brain-memory-ui/` — 正式产品级 UI 模块（Next.js + 独立 API，:3000 + :8000）

建议新项目使用 **brain-memory-ui**。
