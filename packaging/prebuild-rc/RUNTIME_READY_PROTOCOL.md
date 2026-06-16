# CNexus Runtime READY Protocol

> **企业级 boot 语义：** UI 不得 assume Runtime ready；必须等待不可伪造的 `/v1/system/ready`。

---

## 问题定义

| 反模式 | 后果 |
|--------|------|
| UI 启动即 show 悬浮窗 | 麻将块 / 残缺 UI |
| 仅 poll `/v1/health` | HTTP 已监听但 Memory/WS 未就绪 |
| 超时仍 show | 加壳 / 慢盘随机崩 |

---

## READY 条件（v3 — 全部满足）

```text
1. HTTP server listening     → http: "listening"
2. License validated         → license_valid: true (startup gate)
3. Token policy OK           → token_valid: true
4. Memory / storage init     → memory: "ready" | "degraded" | "initializing"
5. WS /ws/state callable     → ws: "alive" (runtime pointer exists)
6. boot_phase                → boot_4_ready (Boot Protocol v3)
7. Response status           → "ready" (evaluate_system_ready)
```

权威调度：`core/runtime/boot_protocol.py` · `evaluate_system_ready()`  
实现：`brain-memory-ui/api/system_ready.py` · 路由 `GET /v1/system/ready`

> v3 变更：`status=ready` **仅**在 `BOOT_4_READY`；BOOT_1–3 一律 `warming`（HTTP 200，禁止 timeout）。

---

## BootStateLock（UI 进程）

```text
STATE 0  INIT
STATE 1  RUNTIME_SPAWNING   ← sidecar spawn
STATE 2  RUNTIME_READY      ← Rust poll /v1/system/ready OK
STATE 3  UI_RENDER_ALLOWED  ← JS probe + grant_ui_render_command
STATE 4  FLOAT_WINDOW_SHOWN ← show_float_window + health re-check
```

**规则：** 仅 `STATE ≥ 3` 允许 `show_float_window`。

源码：`src-tauri/src/boot_state.rs` · `boot_sequence.rs`

---

## 事件

| 事件 | 何时 |
|------|------|
| `cnexus:runtime-ready` | Rust 首次 system/ready OK |
| `cnexus:runtime-boot-timeout` | 30s 内未 ready → UI demo fallback |
| `grant_ui_render_command` | 前端 WS+REST 复检通过后 |
| `boot_fallback_demo_command` | 超时/demo 路径，跳过 Runtime |

---

## UI 等待模型

```text
UI boot → spawn sidecar (STATE 1)
       → poll /v1/system/ready (Rust)
       → READY → emit runtime-ready (STATE 2)
       → JS probeRuntimeReady (REST + WS 2s)
       → grant UI render (STATE 3)
       → delay 120ms → show float (STATE 4)

TIMEOUT → demo preference + boot_fallback_demo → show float (Demo 数据)
```

---

## Gate 验证

`prebuild-release-gate.ps1` GATE 2 静态检查：

- `boot_state.rs` / `RUNTIME_READY` / `/v1/system/ready`
- `DesktopFloatBoot` + `probeRuntimeReady`
- 禁止 timeout fake ready

---

## 与 `/v1/health` 关系

| 端点 | 用途 |
|------|------|
| `/v1/health` | Liveness · 监控 · 轻量探活 |
| `/v1/system/ready` | **Boot gate · 悬浮窗 show 前置条件** |
| `/v1/health/ready` | 深度存储探测（运维） |

Product **不得**仅用 health 决定 show 悬浮窗。
