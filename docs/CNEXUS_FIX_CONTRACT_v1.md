# CNEXUS Runtime Fix Contract v1

> 从尸检反演 → 可执行结构性修复。非性能优化，是 **Control / Cognitive / Storage 三域隔离**。

## 0. Root Cause（升级版，单句）

**event loop 被 runtime 初始化、磁盘 hydrate、同步认知 warmup 占满，control plane 协程长期无法获得调度时间片；HTTP 超时是受害者，不是病因。**

阻塞发生在 **asyncio 主线程**，不是 worker thread 设计失败。

---

## 1. 结构性错误 → 修复义务

| ID | 结构性错误 | 修复义务 | 优先级 |
|----|-----------|----------|--------|
| E1 | Control + Cognitive 共居单 event loop | runtime 构造 **禁止** 在 loop 线程；仅 `cnexus-runtime-warm` 线程 | P0 |
| E2 | `async` handler 外壳化 | 所有 disk full-scan / governance / `get_current_state` 必须 `asyncio.to_thread` 或独立线程 | P0 |
| E3 | warmup 无资源预算 | cognitive warmup 仅在 daemon 线程；禁止 `get_runtime()` 回退 sync 构造 | P0 |
| E4 | hydrate 假异步 | `_hydrate_execution_tap` 整体下沉 `to_thread` | P0 |
| E5 | BOOT 是代码路径非调度器 | Boot Protocol v3 阶段门控 + 可观测 `boot_phase` | P1 |
| E6 | 认知面未进程隔离 | 长期：Runtime sidecar 进程；短期：线程 + to_thread 硬隔离 | P2 |

---

## 2. 时间线（T0–T9，验收基准）

```
T0  uvicorn start
T1  mark_app_started → BOOT_0_API
T2  warm_runtime_background (thread only)
T3  BrainMemoryRuntime.__init__ (worker thread ONLY)
T4  cognitive warmup queued (worker thread ONLY)
T5  hydrate queued → to_thread (never on loop)
T6  event loop MUST remain responsive
T7  GET /v1/system/ready
T8  v1_system_ready scheduled < 50ms
T9  HTTP 200 (warming|ready) — NEVER client timeout while :8000 listening
```

**Acceptance**：sidecar 启动后 30 次 `GET /v1/system/ready`（10s timeout）**零** curl exit 28；允许 `status=warming`，禁止无响应。

---

## 3. 修复层（Fix Layers）与代码锚点

### Layer 1 — Runtime 构造隔离（P0）✅

**文件**：`brain-memory-ui/api/deps.py`

| 禁止 | 必须 |
|------|------|
| `get_runtime()` → `_create_runtime()` on caller thread | `get_runtime()` 仅返回已就绪实例，否则 `RuntimeNotReady` |
| 任意 async handler 触发 inline 构造 | 唯一构造入口：`warm_runtime_background()` → `_work()` |

```python
# Contract:
# _create_runtime() MAY ONLY be called from cnexus-runtime-warm thread
```

### Layer 2 — Hydrate 下沉 worker（P0）✅

**文件**：`brain-memory-ui/api/main.py`, `core/runtime/tap_bootstrap.py`

```python
# Contract:
async def _hydrate_execution_tap():
    await asyncio.to_thread(_hydrate_execution_tap_sync, base_dir)
```

所有 `hydrate_from_disk()` / `configure_*` 在 sync 实现内，**不得**在 event loop 线程执行。

### Layer 3 — Cognitive warmup 限速（P1，待实施）

**文件**：`brain_memory/runtime.py`, `brain-memory-ui/api/deps.py`

- `run_cognitive_warmup()` 已在 `cnexus-cognitive-warm` 线程
- 待办：governance cycle 分片 + `time.sleep(0)` / chunk yield，避免长时间 GIL 霸占

### Layer 4 — `/v1/system/ready` 纯观测（P0，已符合，加固）

**文件**：`api/v1_endpoints.py`, `api/system_ready.py`

| 允许 | 禁止 |
|------|------|
| `peek_runtime()` | `get_runtime()` |
| `fast_health_payload()`（`exists()` only） | `deep_health_payload()` |
| `boot_status()` 内存标志 | `get_current_state()` / CDG / embedding |

### Layer 5 — Boot Protocol v3 状态机（P1）

**文件**：`core/runtime/boot_protocol.py`, `packaging/BOOT_STATE_MACHINE.md`

```
BOOT_0_API          → HTTP listen, ready=warming (immediate)
BOOT_1_STATE        → runtime thread spawn complete
BOOT_2_HYDRATE      → disk hydrate staged (worker thread)
BOOT_2_COGNITIVE    → cognitive warmup throttled (worker thread)
BOOT_3_OPTIMIZED    → full cognitive plane ready
```

每阶段：**可并行、可失败、可重试**；失败不阻塞 ready 响应。

---

## 4. 工程原则（压缩版）

> **Control Plane = IO-free + cognition-free on the event loop thread.**  
> **All cognition / memory / hydrate = detached execution graph (thread or process).**

---

## 5. 实施状态

| Layer | 状态 | 备注 |
|-------|------|------|
| L1 Runtime 隔离 | **已实施** | `get_runtime()` 移除 sync 回退 |
| L2 Hydrate 下沉 | **已实施** | `to_thread` 包裹 |
| L3 Warmup 限速 | 待办 | 需 governance 分片 |
| L4 Ready 纯观测 | 已符合 | 测试锁定 |
| L5 Boot v3 | **已实施** | `docs/CNEXUS_BOOT_PROTOCOL_v3.md` + `evaluate_system_ready()` |

---

## 6. 验证命令

```powershell
# 快速 ready 探针
.\scripts\debug-system-ready.ps1

# 完整 smoke gate
.\scripts\prebuild-smoke-gate.ps1
```

```bash
python -m pytest tests/test_boot_protocol_v2.py tests/test_fix_contract_runtime_isolation.py -q
```
