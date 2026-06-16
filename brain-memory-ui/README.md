# CNexus UI / CNexus Product

**CNexus Product** — 可独立部署的 Mind UI（Demo 离线 + 可选 Runtime 绑定）。  
**CNexus Runtime** — FastAPI + `brain_memory` 认知内核（可单独运行）。

## 架构

```text
┌─────────────────────────────────────────────────────────┐
│  CNexus Product (frontend/)          :3000              │
│  Demo 模式 ── mock MindOverview（零 API）               │
│  Runtime 模式 ── GET /v1/mind/overview + WS /ws/state   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / WebSocket（契约，不 import Python）
              ┌────────▼────────┐
              │  Runtime API    │  :8000  (api/)
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  CNexus Core    │  brain_memory/
              └─────────────────┘
```

> 独立部署说明见 **[PRODUCT.md](./PRODUCT.md)**

## 快速启动

### A. 仅 CNexus Product（Demo，无需后端）

```powershell
.\brain-memory-ui\scripts\start-product.ps1
```

浏览器 → **http://localhost:3000** → 选择 **加载 CNexus Demo**

### B. Product + Runtime 组合

```powershell
.\brain-memory-ui\scripts\start.ps1
```

或 Docker 全栈：

```bash
cd brain-memory-ui
docker compose -f docker-compose.full.yml up --build
```

### C. Docker 仅 Product

```bash
cd brain-memory-ui
docker compose -f docker-compose.product.yml up --build
```

## API 契约（Product 消费面）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/mind/overview` | **稳定契约** — Mind 概览快照 |
| GET | `/health` | 健康检查 |
| POST | `/chat` | 对话（Runtime 模式） |
| GET | `/memory/recall?query=` | 搜索 |
| POST | `/memory/capture` | 写入 |
| WS | `/ws/state` | 状态流（含 `mind_overview`） |

完整说明：[docs/CNEXUS_PRODUCT_API.md](./docs/CNEXUS_PRODUCT_API.md)

## 配置 Runtime 地址

```bash
# frontend/.env.local
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_WS_BASE=ws://localhost:8000
```

Docker 运行时（无需 rebuild）：

```bash
-e CNEXUS_API_BASE=http://localhost:8000
-e CNEXUS_WS_BASE=ws://localhost:8000
```

## 目录

```text
brain-memory-ui/
├── frontend/              # CNexus Product (cnexus-product npm)
├── api/                   # Runtime API
├── Dockerfile.runtime     # Runtime 镜像
├── docker-compose.product.yml
├── docker-compose.full.yml
├── PRODUCT.md             # 独立产品部署
├── scripts/
│   ├── start-product.ps1  # UI only
│   └── start.ps1          # UI + Runtime
└── docs/
```
