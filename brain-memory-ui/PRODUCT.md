# CNexus Product — 独立产品部署

CNexus Product 是**可单独运行**的 Mind UI，通过 HTTP/WS 契约可选绑定 Runtime。

## 三种部署

| 方式 | 命令 | 说明 |
|------|------|------|
| **本地 Demo** | `.\scripts\start-product.ps1` | 零后端，选「CNexus Demo」 |
| **Product Docker** | `docker compose -f docker-compose.product.yml up --build` | 容器化 UI，Demo 可用 |
| **Full Stack** | `docker compose -f docker-compose.full.yml up --build` | UI + Runtime API |
| **Runtime only** | `docker compose -f docker-compose.runtime.yml up --build` | 仅 Runtime API |

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `CNEXUS_API_BASE` | `http://localhost:8000` | Runtime REST（浏览器可访问的 URL） |
| `CNEXUS_WS_BASE` | `ws://localhost:8000` | Runtime WebSocket |
| `CNEXUS_PRODUCT_PORT` | `3000` | Product 端口 |
| `CNEXUS_RUNTIME_PORT` | `8000` | Runtime 端口（full stack） |

Docker 启动时写入 `public/cnexus-config.json`，**无需重新 build** 即可改 Runtime 地址。

## 契约（UI 唯一依赖）

```
GET  /v1/mind/overview   → MindOverview JSON
WS   /ws/state           → 含 mind_overview 字段
POST /chat               → Runtime 模式对话
GET  /memory/recall      → Runtime 模式搜索
```

详见 [docs/CNEXUS_PRODUCT_API.md](./docs/CNEXUS_PRODUCT_API.md)

## 本地开发

```bash
cd frontend
cp .env.example .env.local   # 可选
npm install
npm run dev
```

打开 http://localhost:3000 → 选择 Demo 或连接 Runtime。

## 单独构建镜像

```bash
cd frontend
docker build -t cnexus-product .
docker run --rm -p 3000:3000 \
  -e CNEXUS_API_BASE=http://host.docker.internal:8000 \
  cnexus-product
```

## 与 monorepo 的关系

- **CNexus Product** = `frontend/`（可抽离为独立仓库）
- **Runtime Service** = `api/` + `brain_memory/`（Python 内核）
- 组合运行：`scripts/start.ps1` 或 `docker-compose.full.yml`
