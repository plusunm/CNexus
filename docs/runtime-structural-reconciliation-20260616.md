# CNexus Runtime 不稳定 — 结构剖面对账报告

**对账日期：** 2026-06-16  
**对账范围：** 三维排查框架 + HCRS/DBSM 结构剖面 vs 当前代码库  
**性质：** 纯根因剖面 / 证据对齐 — **不含修复方案**  
**撰写人：** Auto（Cursor AI 编码助手）

---

## 零、对账总裁决

| 你的核心论断 | 代码对账 |
|-------------|---------|
| 问题本质是「非确定性收敛系统」被建模成「强同步状态机」 | ✅ **成立** — 见 §五 |
| P0 在 Boot/认知协议，不在前端、不在构建 | ✅ **成立**（构建为 P2 观测干扰） |
| 「修了观测层，动力层未变」 | ✅ **成立** |
| BOOT_4 ↔ cognitive ↔ IO 形成代码级死锁环 | ⚠️ **表述需修正** — 非真循环依赖，是 **单层 AND 门控**（§五·2） |
| Ollama 无超时导致启动挂死 | ⚠️ **部分成立** — Ollama 非 BOOT_3 L3 主链硬依赖；embedding 在 background hydrate 异步路径 |
| 用户 PYTHONPATH 污染 bundle | ❌ **生产路径不成立** — sidecar 显式 `env_remove("PYTHONPATH")` |
| 前端 probe 导致上线/离线抖动 | ✅ **机制成立** — 单次失败即 offline + 8s 超时 |
| SKIP=1 是协议层二分法 | ✅ **成立** — `cognitive_disabled()` 直跳 BOOT_4 |

**一句话对账：**

> 你的 **HCRS→DBSM 误建模** 框架与代码 **高度一致**；「死锁环」应改为 **「三层异步收敛被 AND 成一个 ready 布尔量」**；Windows 环境项 **部分已在 sidecar 隔离**，但仍需 Procmon/stderr **运行时取证** 才能闭合 I/O 层。

---

## 一、三维排查框架 — 从外向内对账

### 1.1 外部环境与启动链路（底层隔离性）

| 排查项 | 你的假设 | 代码事实 | 对账 |
|--------|---------|---------|------|
| **进程/文件锁** | Procmon 见 kuzu_db/lancedb `ACCESS DENIED` / `SHARING VIOLATION` | sidecar **不再**预建 `kuzu_db` 空目录；`ensure_runtime_data_dirs` 只建 parent；`blocks`/`lancedb` 仍预建 | ⚠️ **代码已防一类 Kuzu 锁**；并发锁需 **Procmon 实测**，代码无法证伪 |
| **僵尸 python 占端口** | 残留 `python.exe` 致新进程秒退 | sidecar 日志写 `runtime-api.stderr.log`；exit code 在 `runtime-sidecar.log`；`BM_API_PORT=8000` | ⚠️ **机制存在**；是否为用户主因 **未闭合** |
| **Python 环境污染** | 系统 PYTHONPATH 污染 site-packages | ```118:122:brain-memory-ui/frontend/src-tauri/cnexus-runtime-sidecar/src/main.rs``` 先 `cmd.env(...)` 再 **`env_remove("PYTHONHOME")` / `env_remove("PYTHONPATH")`**；使用 bundle 内 `pythonw.exe`；`PYTHONNOUSERSITE=1` | ❌ **用户 PYTHONPATH 污染论断在打包路径下不成立**；子进程 **故意清空 PYTHONPATH**，依赖 embedded Python 自身路径配置 |
| **编码异常** | stderr 中 `UnicodeDecodeError`；需 PYTHONUTF8 | sidecar 设 `PYTHONIOENCODING=utf-8`、`PYTHONUTF8=1`；`windows_subprocess` 有 UTF-8 注入 | ✅ **防护已写入 sidecar**；历史日志是否仍报错需 **stderr 取证** |
| **sidecar exit code** | 内核层看 Python 子进程退出码 | sidecar `wait()` 后写 `API process exited code=` 并 `exit(code)` | ✅ **可观测** — `%LOCALAPPDATA%\CNexus\data\runtime-sidecar.log` |

**本层结论：** 代码对 Windows 执行上下文做了 **隔离意图**（bundle Python、清 PYTHONPATH、UTF-8）。**不能**在缺 Procmon/stderr 的情况下把 I/O 锁升为主因；但若 **SKIP=1 仍无法 ready**，本层 **升级为 P0 并列排查**（与你的会诊表一致）。

---

### 1.2 认知启动协议（逻辑阻塞点）

| 排查项 | 你的假设 | 代码事实 | 对账 |
|--------|---------|---------|------|
| **SKIP 二分法** | SKIP 后秒级 Ready → 阻塞在 cognitive | `cognitive_disabled()` 读 `CNEXUS_BOOT_SKIP_COGNITIVE` 等；`mark_runtime_spawned` / `mark_hydrate_complete` 路径直接 `mark_cognitive_warmup_done(bypass_causal=True)` | ✅ **二分逻辑在代码中硬编码** |
| **BOOT_4 必要条件含 cognitive** | 认知就绪是 ready 必要项 | ```485:489:core/runtime/boot_protocol.py``` `phase != BOOT_4_READY` → warming；`_cognitive_warmup_blocks_ready()` → warming | ✅ **完全成立** |
| **cognitive 后台不阻塞 API** | 应改为 async enhancement | `start_cognitive_warmup_background()` 注释写「never blocks control-plane」— **指 HTTP 线程不阻塞**；但 **`evaluate_system_ready` 仍因 BOOT_3/4 返回 warming** | ⚠️ **半真**：线程隔离有，**语义门控未隔离** — 这正是结构矛盾 |
| **Ollama 无超时挂死** | 等永不回复的 Embedding | `core/ollama_manager.py` probe `timeout=2`；BOOT_3 `CognitiveWarmupAdapter` 任务为 cdg/memory/governance/reflection **L3 tick**，**不直接 HTTP 调 Ollama**；embedding 预加载在 `background_hydrate._hydrate_embedding` **独立线程** | ⚠️ **「Ollama 挂死 boot」在代码链路上不精确**；更精确是 **L3 队列 + adapter.done + 多 tier idle 检查** 长期不满足 `_cognitive_warmup_blocks_ready()` |
| **120s 超时逃生** | — | `maybe_advance_cognitive_timeout()`：deploy=`internal`（sidecar 默认）时 120s 可 `bypass_causal` 进 BOOT_4 | ✅ 存在，但是 **超时后强制收敛**，不是 **能力分层** |
| **warmup 线程失败行为** | — | `start_cognitive_warmup_background` except 时 log **「holding BOOT_3 (no optimistic BOOT_4)」** | ✅ **失败即长期 warming** |

**本层结论：** 「认知就绪 = BOOT_4 必要条件」**代码级确认**。你的 **协议定义错误** 论断成立。Ollama 应归入 **认知/IO 长尾子系统**，不宜单独写成 boot 链路上的唯一阻塞点。

---

### 1.3 门控语义竞态（前端感知层）

| 排查项 | 你的假设 | 代码事实 | 对账 |
|--------|---------|---------|------|
| **Monitor vs Status 频率不一致** | 轮询与全局状态频率不同 | `useFloatRuntimeMonitor`：boost 500ms / watch 2500ms / idle 60s；`useRuntimeStatus` **不独立轮询**，合并 monitor + MindStore fallback | ✅ **成立** — 且 **MindStore 另有** `probeRuntime` / `probeRuntimeFull` / `hydrateRuntimeData` |
| **ready 延迟 → 判离线抖动** | 连续失败导致上线/离线振荡 | `runProbe` catch **一次**即 `phase=offline`；`RUNTIME_PROBE_TIMEOUT_MS=8000`；单次 probe 串行 **fast + full** 两次 ready | ✅ **机制完全成立** |
| **ensureMemoryWriteReady 过短超时** | 8s 硬编码 | `memoryWriteReady` → `probeRuntimeFull` → `systemReadyFull` 用 **8000ms**；再调 `memoryStats()` | ✅ **成立** |
| **乐观就绪（TCP 活即上传）** | 建议 fail-safe | 当前 `canWriteMemory` / `canUseRuntimeApi` **绑定** `runtimeReady`（= full ready 语义） | ✅ 对账确认：**前端无乐观就绪**；与你的「应用层 a 应允许、认知层 warming」**目标态**相反于 **现实现状** |
| **多 probe 源** | — | 至少：`FloatMonitor`、`MindStore.probeRuntime*`、`FrontendBootstrapGate`、`useExecutionStatus.probeRuntimePhase`、`ensureMemoryWriteReady` | ✅ **观测层叠加** 与你判断一致 |

**本层结论：** 前端是 **P1 放大器**，不是 P0。你的「状态显示比实际状态更混乱」**成立** — 因 **多源观测 + 短超时 + 无 offline 去抖**。

---

## 二、会诊排查建议表 — 对账

| 排查层次 | 你的操作手段 | 代码侧可提供的锚点 | 对账状态 |
|---------|-------------|-------------------|---------|
| **内核层** | stderr 末行 / exit code | `runtime-api.stderr.log`、`runtime-sidecar.log` | ✅ 路径明确 |
| **I/O 层** | Procmon | Kuzu 路径逻辑在 `storage/graph.py`、`core/paths.py` | ⚠️ 需实测 |
| **协议层** | full ready JSON；SKIP 对比 | `GET /v1/system/ready?mode=full` → `evaluate_system_ready`；fast 默认 → `ready_fast` **另一套语义** | ✅ 必须 **强制 mode=full** |
| **接口层** | 门控 vs API 匹配 | `useMindOverview`: `isLive = runtimeReady`；与 `ready_fast` 已脱钩 | ✅ 已收紧但仍 **多 probe** |

**你的结论性判断对账：**

- **SKIP=1 仍无法启动** → 停改前端，查 NSIS/依赖/路径：**与代码设计一致**（此时 P0 不在 cognitive 协议）。
- **SKIP=1 正常** → 必须解耦 cognitive 与 API ready：**与 `evaluate_system_ready` 现状矛盾**，确认为 **唯一架构级出路**（此处仅定性，不给方案）。

---

## 三、HCRS / DBSM 结构剖面 — 逐条对账

### 3.1 核心矛盾：异步认知 vs 同步门控

**你的表述：**

> 认知层是 emergent；系统却要求 BOOT_4 才放行。

**代码映射：**

```
[Deterministic API]  FastAPI + boot_protocol.evaluate_system_ready()
        ∧ (AND)
[Stochastic Cognitive]  CognitiveWarmupAdapter L3 ticks → mark_cognitive_warmup_done
        ∧ (AND)
[Eventual Memory]  runtime warm + hydrate + memory_ok + cached health
        ‖
        ↓ 压缩为
   单一 status: "ready" | "warming"
```

✅ **与「三层压成一个状态机」完全一致。**

---

### 3.2 「死锁环」表述修正

**你的闭环图：**

```
BOOT_4 → cognitive warmup → IO readiness → BOOT_4
```

**代码实际（非环，是链 + 门）：**

1. `warm_runtime_background()` — **不等待** BOOT_4，独立线程 `_create_runtime()`  
2. `mark_hydrate_complete()` → BOOT_3  
3. `start_cognitive_warmup_background()` → `run_cognitive_warmup_ticks` → 成功则 `mark_cognitive_warmup_done()` → BOOT_4  
4. **`evaluate_system_ready()` 在 1–3 完成前始终 warming** — 这是 **门控**，不是 **runtime 无法初始化**

更准确的一句话：

> ❗不是进程级死锁，而是 **报告态（reported readiness）等待最慢子系统收敛** 的 **同步幻觉**。

你的 **「统一状态幻想」** 表述比 **「死锁环」** 更贴近代码。

---

### 3.3 为什么「修哪里都没用」

| 你列的修改 | 代码中属于 | 是否改变 `evaluate_system_ready` |
|-----------|-----------|--------------------------------|
| ready/reason/progress 字段 | 观测层 | ❌ |
| 前端 probe / 门控收紧 | 观测层 | ❌ |
| timeout / progressive 120s | 观测+逃逸 | ⚠️ 仅 **延迟** 强制 BOOT_4 |
| Kuzu/UTF-8/build | 环境/交付 | ❌ 不改变 AND 语义 |
| Fast-Path `ready_fast` | 观测 fast lane | ❌ 与 full ready **双轨** |

✅ **「观测层改善、动力层不变」对账成立。**

---

### 3.4 现象 → 本质 统一解释表（对账）

| 现象 | 你的本质 | 代码锚点 |  |
|------|---------|---------|--|
| 长期 warming | 收敛未完成 + gate 阻断 | `boot_ready_details` reason=`COGNITIVE_WARMUP` / `BOOT_PHASE_*` | ✅ |
| ready 不一致 | 多子系统 + 多 probe | fast=`ready_fast` vs full=`evaluate_system_ready` | ✅ |
| 上传失败 | memory/API 未过 gate | `canWriteMemory` 需 `runtimeReady` | ✅ |
| 偶发可用 | stochastic 波动 | 120s timeout bypass；warm 线程竞态 | ✅ |
| 构建误导 | 版本不一致 | BAT exit -1（文档已述） | ✅ |

---

## 四、关键定性 — 「不是这些问题」对账

| 你的排除项 | 对账 |
|-----------|------|
| ❌ 前端门控太严格 — 非根因 | ✅ 门控是 DBSM 的 **下游表现** |
| ❌ HTTP ready 判断错误 — 非根因 | ⚠️ **双轨 API（fast/full）是观测层设计债**，强化「多 truth」 |
| ❌ UI 状态同步 — 非根因 | ✅ P1 放大器 |
| ❌ CMD 闪窗 — 非根因 | ✅ sidecar 用 `CREATE_NO_WINDOW`；闪窗若存在，属 **其他 spawn 路径**，不解释 warming |

| 不能排除的并行子因（你未强调） | 对账 |
|--------------------------------|------|
| Runtime warm **初始化异常**（Kuzu/Lance/路径） | `deps._create_runtime` except → `record_runtime_warm_attempt(init_error=...)` → **永不 BOOT_4** |
| **enterprise** deploy 无 120s bypass | sidecar 默认 `CNEXUS_DEPLOY_LEVEL=internal` — desktop personal **有** bypass |
| sidecar **清空 PYTHONPATH** | 若 embedded python 路径配置错误 → **仅特定机器** 启动失败（与「用户 PYTHONPATH 污染」不同机理） |

---

## 五、系统分类对账

| 你的分类 | 代码体现 |
|---------|---------|
| **HCRS**（Hybrid Cognitive Runtime System） | BrainMemoryRuntime + Ollama + LanceDB/Kuzu + L3 governance 异步共存 |
| **DBSM**（Deterministic Boot-State Machine） | `BootPhase` 枚举线性 + `evaluate_system_ready()` 布尔输出 + UI `runtimeReady` 单比特 |

✅ **分类准确。** 不稳定来自 **用 DBSM 的「ready」去代表 HCRS 的「当前能力截面」**。

---

## 六、对账后的「单因果链」最终形态

整合你的三维框架 + 结构剖面 + 代码证据：

```
┌─────────────────────────────────────────────────────────────┐
│ 结构根因（P0）                                               │
│  三层异步收敛 ──AND──► 单一 ready 布尔 ──► BOOT_4 同步门    │
└───────────────────────────┬─────────────────────────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   认知 L3 长尾      Memory/IO 次因链      环境/锁（需取证）
   BOOT_3 阻塞       warm init 失败        Procmon/stderr
         │                  │                  │
         └──────────────────┴──────────────────┘
                            │
                            ▼
              evaluate_system_ready → "warming"
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 放大（P1）  多 probe + 8s timeout + fast/full 双轨 → UI 抖动 │
│ 干扰（P2）  构建/包版本不一致 → 观测结论互相否定              │
└─────────────────────────────────────────────────────────────┘
```

---

## 七、尚未闭合（仅列缺口，不给方案）

以下 **无法** 仅靠静态代码对账完成：

1. 用户机 Procmon：kuzu_db / lancedb 是否存在 SHARING VIOLATION  
2. 用户机 `runtime-api.stderr.log`：是否有 init_error / UnicodeDecodeError  
3. 用户机 SKIP=1 vs SKIP=0 的 **full ready JSON 耗时曲线**  
4. 11:04 基线包内 embedded python 在 **无 PYTHONPATH** 下是否 100% 可重复导入 `api.main`  

---

## 八、对账结论（决策用，无修复项）

1. **你的结构剖面（HCRS 误作 DBSM）与代码一致** — 这是「为什么一直不稳定」的 **正确语言**。  
2. **三维排查框架可用** — 顺序应为：**协议层 SKIP 二分 → I/O 取证 → 前端仅作现象确认**。  
3. **「死锁环」应改为「AND 门控 + 最慢子系统主导」** — 避免排查时找不存在的循环依赖。  
4. **前端/超时/probe 是真实放大器** — 但不改变 P0 定性。  
5. **环境 PYTHONPATH 污染在 sidecar 生产路径已被否定**；替换为 **embedded 路径配置 / 文件锁 / warm init 失败** 三类可验证子因。  
6. **继续改观测层而不改 `evaluate_system_ready` 的 AND 语义，动力层不变** — 与你「修哪里都没用」完全一致。

---

**相关文档：**

- `docs/runtime-status-report-20260616.md` — 单因果链定界报告  
- `docs/incident-runtime-consultation-20260616.md` — 会诊检查表  

**对账人：** Auto（Cursor AI 编码助手）  
**日期：** 2026-06-16
