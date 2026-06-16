# CNexus Runtime Contract — RC 0.1.0-alpha

**Release Candidate · 冻结公开 API**

Product（CNexus UI）与 Runtime（FastAPI sidecar）之间只允许通过本文档列出的 HTTP/WebSocket 路径通信。  
内部实现（`core/`、`brain_memory/`、路由重构）可自由演进，**不得破坏下列契约**。

产品版本：`0.1.0-alpha`（见仓库根目录 `VERSION`）

---

## 稳定性承诺

| 级别 | 含义 |
|------|------|
| **Stable** | RC 及后续 patch 保持路径、方法、响应形状；仅可加可选字段 |
| **Deprecated** | 仍可用，响应头含 `Deprecation`；下一大版本移除 |
| **Internal** | 不保证稳定，Product 不得依赖 |

---

## Stable · REST

### `GET /v1/health`

存活探测（进程已监听端口，**不**代表可渲染 UI）。

```json
{ "status": "ok", "service": "cnexus", "version": "0.1.0-alpha" }
```

### `GET /v1/system/ready`

**权威 Runtime READY 信号。** Desktop UI **必须**在收到 `status: ready` 且 WS 握手成功后才允许 show 悬浮窗。

```json
{
  "status": "ready",
  "boot_id": "hex-uuid",
  "token_valid": true,
  "license_valid": true,
  "ws": "alive",
  "http": "listening",
  "memory": "ready",
  "uptime_ms": 1234,
  "version": "0.1.0-alpha"
}
```

未就绪时 HTTP **503**。语义见 `packaging/prebuild-rc/RUNTIME_READY_PROTOCOL.md`。

### `GET /v1/mind/overview`

Mind 仪表盘快照。响应必须符合 `MindOverview`（`frontend/lib/runtimeTypes.ts` + `cnexus-kernel/MindOverviewContract.ts`）。

- 顶层必填：`schema_version`, `generated_at`, `cards`, `feeds`, `system`, `chat_context`, `memory_items`
- `schema_version` 当前：`1.0.0`（与产品版本独立）

### `POST /v1/memory/capture`

写入记忆。

请求：`{ "role", "content", "layer", "importance" }`  
响应：`{ "memory_id", "status" }`

### `GET /v1/memory/recall?query=`

检索记忆上下文。

响应：`{ "context": string }`

### `GET /v1/memory/stats`

记忆统计（Dashboard / Memory 面板可选）。

### `POST /v1/memory/maintenance`

记忆代谢维护（可选，运维/高级 UI）。

---

## Stable · WebSocket

### `WS /ws/state`

约 2s 推送 `RuntimeState`，须含 `mind_overview` 字段（与 `GET /v1/mind/overview` 同形）。

---

## Deprecated（RC 仍保留）

| 路径 | 替代 |
|------|------|
| `GET /health` | `GET /v1/health` |
| `POST /memory/capture` | `POST /v1/memory/capture` |
| `GET /memory/recall` | `GET /v1/memory/recall` |

Product UI **已切换至 `/v1/*`**。旧路径仅供过渡期兼容。

---

## Internal（Product 勿用）

`/chat`, `/governance/*`, `/models/*`, `/logs/*`, `/reflective/*`, `/v1/interact`, OpenAI 兼容层等 — 运维或后续版本再纳入契约。

---

## 验证

```bash
# Python 契约测试
python -m pytest tests/test_cnexus_runtime_contract.py -q

# 桌面打包前
cd brain-memory-ui/frontend
npm run prebuild:check
npm run tauri:build
```

安装后手动验收链：

```
Setup.exe → 安装 → CNexus.exe → cnexus-runtime.exe → GET /v1/health → Memory 面板
```
