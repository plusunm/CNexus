# CNexus Runtime 会诊 — 最终对账闭合表

**日期：** 2026-06-16  
**阶段：** Architecture Correction Phase（因果模型已闭合，待会诊现场二分 + 架构决策）  
**基线包：** `CNexus_0.1.0-alpha_x64-setup.exe`（2026-06-16 11:04）  
**撰写人：** Auto（Cursor AI 编码助手）

---

## 一、会诊开场：三句话定界

1. **不是没启动** — API 进程可以 alive，但 `evaluate_system_ready()` 在 BOOT_4 前一律返回 `warming`。  
2. **不是前端 bug** — 前端多 probe 是 **P1 放大器**；P0 是 **BDE-1**：认知 warmup 被绑进同步 AND 门。  
3. **不是继续 debug** — SKIP=1 若成立，则进入 **协议层手术**（拆分 readiness 语义），而非再加 log/probe。

---

## 二、工程判决（F1–F4，会诊不可再争论）

| ID | 判决 | 代码锚点 | 实验/逻辑 |
|----|------|---------|----------|
| **F1** | `BOOT_4` = **组合 AND 门**，不是单一阶段 | `evaluate_system_ready()` L485–499 | 任一子系统未收敛 → `warming` |
| **F2** | **Dual Reality API** — 同进程两种 ready 语义 | `fast_ready_snapshot` → `ready_fast`；`?mode=full` → evaluate | UI 分裂感知 |
| **F3** | **SKIP=1 = 因果 ablation** | `cognitive_disabled()` → `bypass_causal` → BOOT_4 | 开发机已验证 |
| **F4** | 稳定性 = **最慢 stochastic 子系统** | BOOT_3 L3 + `_cognitive_warmup_blocks_ready()` | 数学必然，非偶发 |

**BDE-1 定义：**

> 把 **非确定性收敛子系统（cognitive/LLM）** 的完成事件，作为 **全局 `ready` 布尔量的同步前提**。

---

## 三、语义校正（会诊口述时必须用对）

### 3.1 `_cognitive_warmup_blocks_ready()` 方向

**错误表述（避免）：**

> 「必须等 `_cognitive_warmup_blocks_ready() == True` 才放行」

**正确表述：**

> 「当 `_cognitive_warmup_blocks_ready()` **为 True（仍在阻塞）** 时，`evaluate_system_ready()` 返回 `warming`；只有其为 **False** 且 `boot_phase == boot_4_ready` 时才可能 `ready`。」

```485:489:core/runtime/boot_protocol.py
    if runtime_warming or phase != BootPhase.BOOT_4_READY:
        return "warming"

    if _cognitive_warmup_blocks_ready():
        return "warming"
```

### 3.2 「cognitive 后台线程 ≠ 语义非阻塞」

`start_cognitive_warmup_background()` 注释：**不阻塞 HTTP 线程**。  
但 **`evaluate_system_ready()` 仍被 cognitive 状态阻塞** — 会诊必须区分 **线程隔离** 与 **语义门控**。

### 3.3 120s timeout 的定位

`maybe_advance_cognitive_timeout()`（internal 部署默认适用）= **时间换状态**，不是 Progressive Capability Model。  
用户在 **0–120s** 内仍可能被 **全功能门控**（`runtimeReady` 单比特）。

---

## 四、权威 ready 公式（会诊白板版）

```text
full_ready ("ready")
  ⇔ app_started
  ∧ ¬runtime_warming
  ∧ boot_phase == BOOT_4_READY
  ∧ ¬_cognitive_warmup_blocks_ready()    ← cognitive/L3/tier idle 组合
  ∧ runtime_present
  ∧ memory_ok
  ∧ token/license valid

default GET /v1/system/ready
  → 常走 fast_ready_snapshot
  → status: "ready_fast"                 ← 不经过上式
```

---

## 五、P0 / P1 / P2 分层（会诊统一词汇）

| 层 | 名称 | 本质 | 会诊动作 |
|----|------|------|---------|
| **P0** | BDE-1 | 同步 AND 门 + cognitive 绑定 | **架构决策**：拆 operational / full |
| **P1** | 感知放大 | ≥6 路 probe + 8s 超时 | **冻结**：会诊期不再加 probe |
| **P2** | 交付噪声 | BAT exit -1、旧 LocalAppData | **基线包 + 清目录** 后再判 |

---

## 六、前端 Probe 清单（P1 证据 — 会诊对照用）

| # | 模块 | 调用 | 路径 |
|---|------|------|------|
| 1 | MindStore | `probeRuntime` (fast) | `MindStore.ts` |
| 2 | MindStore | `probeRuntimeFull` | `MindStore.ts` |
| 3 | MindRuntimeBridge | 定时 probe + hydrate | `MindRuntimeBridge.tsx` |
| 4 | FloatMonitor | fast + full 串行 | `useFloatRuntimeMonitor.ts` |
| 5 | memoryWriteReady | `probeRuntimeFull` + stats | `memoryWriteReady.ts` |
| 6 | FrontendBootstrapGate | fast / SSE / full | `FrontendBootstrapGate.ts` |
| 7 | useExecutionStatus | `probeRuntimeReady` | `useExecutionStatus.ts` |
| 8 | resolveRuntimeConnectionDisplay | 合成 `canUseRuntimeApi` | `runtimeConnection.ts` |

**门控比特：** `useMindOverview` → `isLive = runtimeReady`；`canWriteMemory` 同 gate。  
**超时：** `RUNTIME_PROBE_TIMEOUT_MS = 8000`（`api.ts`）。

**结构缺口确认：** grep 全库 **无** `operational_ready` / `full_ready` / `ready_for_chat` / `/v1/system/capability`。

---

## 七、前因 → 机制 → 后果（会诊单页链）

```text
前因   HCRS 需求 + DBSM 实现 + Fast/Full 双轨妥协
  ↓
机制   ready = ∧(子系统)；cognitive 非确定；Dual Reality；多 probe
  ↓
后果   0–120s warming；状态分裂；上传/聊天假离线
  ↓
修复史 观测层改善（reason/UTF-8/Kuzu）→ 动力层不变
  ↓
实验   SKIP=1 → 秒级 BOOT_4 → P0 因果闭合
  ↓
判决   模型 mismatch — Architecture Correction Phase
```

---

## 八、会诊现场：已闭合 vs 待证

| 项 | 状态 | 说明 |
|----|------|------|
| F1–F4 代码语义 | ✅ **已闭合** | 静态对账 + 公式 |
| SKIP=1 开发机 | ✅ **已闭合** | 协议 ablation 成立 |
| SKIP=1 **用户机 + 11:04 包** | ⏳ **待证** | 会诊 Phase II |
| full ready JSON（无 SKIP） | ⏳ **待证** | curl 三连 + reason |
| Procmon 文件锁 | ⏳ **待证** | 仅当 SKIP 仍失败时升 P0' |
| CMD 闪窗 | ⏳ **待证** | 并行 UX，不解释 BDE-1 |
| Step 1 代码改造 | ✅ **工作区已实现** | operational/capability/SSOT/conflict_log；**待新 NSIS 包用户验收** |

---

## 九、120 分钟会诊执行表（与对账对齐）

| 阶段 | 时间 | 动作 | 通过 → 含义 | 失败 → 含义 |
|------|------|------|------------|------------|
| **0** | 0–10 min | 确认 **本轮新 NSIS 包**（非 11:04 旧基线）；删 `%LOCALAPPDATA%\CNexus` | 版本一致 | 结论无效 |
| **I** | 10–40 min | curl capability + full + memory/stats + conflict_log | 记录 operational/full/reason | 端口/进程问题 → P0' |
| **II** | 40–70 min | `CNEXUS_BOOT_SKIP_COGNITIVE=1` 冷启 | full ready ≤30s | **停改前端**；查 stderr/sidecar |
| **III** | 70–95 min | 关 SKIP，测无 SKIP 耗时曲线 + UI chat/upload | 量化 cognitive 窗口 + Step 1 体感 | BDE-1 用户体感数据 |
| **IV** | 95–120 min | **架构决策** | Step 2 范围（D1–D4） | 见 §十 + [deep-consultation](runtime-deep-consultation-round-20260616.md) |

**curl 三连（PowerShell）：**

```powershell
curl.exe -s --max-time 15 "http://127.0.0.1:8000/v1/system/capability"
curl.exe -s --max-time 15 "http://127.0.0.1:8000/v1/system/ready?mode=full"
curl.exe -s --max-time 15 "http://127.0.0.1:8000/v1/memory/stats"
curl.exe -s --max-time 15 "http://127.0.0.1:8000/v1/system/conflict_log?tail=50"
```

## 打包内置（安装后落盘）

| 资源 | 打包路径 | 安装后路径 |
|------|---------|-----------|
| 日志模板 | `runtime-bundle/app/data-templates/runtime-conflict-monitor.log` | `%LOCALAPPDATA%\CNexus\data\runtime-conflict-monitor.log` |
| 说明文件 | `.../runtime-conflict-monitor.README.txt` | 同目录 README |

- **NSIS 安装**：`hooks.nsh` 首次安装时从 bundle 复制模板  
- **Sidecar 启动**：若日志不存在，从 bundle 模板或内联 seed 初始化  
- **构建校验**：`verify-runtime-bundle.ps1` 检查模板 + `conflict_monitor` 模块导入

**日志路径：**

- `%LOCALAPPDATA%\CNexus\data\runtime-api.stderr.log`
- `%LOCALAPPDATA%\CNexus\data\runtime-sidecar.log`
- **`%LOCALAPPDATA%\CNexus\data\runtime-conflict-monitor.log`** — **Runtime 冲突专用 JSONL 审计日志**（capability 状态、Dual Reality、Boot 相位、前端 probe 异常）
- 在线 tail：`GET http://127.0.0.1:8000/v1/system/conflict_log?tail=200`

---

## 十、会诊决策点（只选架构，不选 patch）

### 决策 A — SKIP=1 通过（预期）

**裁定：** P0 = BDE-1 定案。  
**批准范围（Step 1 PR）：**

1. 后端：拆分 **operational_ready** / **full_ready**（不删 evaluate，增语义层）  
2. API：ready payload 增 **capabilities**；规划 `/v1/system/capability`  
3. 前端：**冻结新 probe**；收敛 SSOT（单 capability 订阅）  
4. cognitive：**语义解耦 BOOT_4**（后台 + 事件，非阻塞 operational）

**禁止：** 继续改 timeout、加 FloatMonitor 逻辑、仅加 reason 文案。

### 决策 B — SKIP=1 仍失败

**裁定：** 并列 **P0'**（runtime warm / IO / 打包）。  
**动作：** Procmon + stderr + sidecar exit code；**暂停** readiness 语义手术直到 API 能稳定 listen。

---

## 十一、Step 1 范围对账（2026-06-16 工作区状态）

| Step | 目标 | 当前代码 | 会诊验收 |
|------|------|---------|---------|
| 1 | operational vs full | ✅ `evaluate_operational_ready` + capability payload | 新包 curl + UI |
| 2 | cognitive 不挡 operational | ✅ 语义层已拆；full 仍等 BOOT_4 | operational 后 chat |
| 3 | UI capability SSOT | ✅ `MindStore.syncSystemCapability` | 无多 probe 抖动 |
| 4 | `/v1/system/capability` | ✅ 已实现 | conflict_log 有 CAPABILITY_STATE |
| 5 | conflict monitor 入包 | ✅ bundle + NSIS + sidecar seed | 安装后日志存在 |

**预期体感（架构目标，非承诺数值）：** operational 后 **chat/基础交互** 可用；upload 可绑定 `memory_ok` / full；LLM warming 仅提示不全局锁。

---

## 十二、会诊禁语 / 必用语

| 禁语 | 原因 |
|------|------|
| 「再加强一下前端轮询」 | 放大 P1 |
| 「把 timeout 调到 30s」 | 时间替代状态 |
| 「ready_fast 也算 online」 | 重现 Dual Reality |
| 「BOOT_4 是 bug」 | 是实现公理，非实现错误 |

| 必用语 | 含义 |
|--------|------|
| BDE-1 | cognitive 同步门控 |
| Dual Reality | fast vs full |
| operational_ready | 待建 Layer 1 |
| 因果已闭合 | F1–F3 + SKIP ablation |

---

## 十三、文档索引（对账链完整）

| 文档 | 用途 |
|------|------|
| `docs/runtime-deep-consultation-round-20260616.md` | **本轮深度会诊执行手册（主脚本）** |
| `docs/runtime-consultation-closure-20260616.md` | 会诊闭合表 + 120min 表 |
| `docs/runtime-engineering-verdict-20260616.md` | 工程判决 + 前因后果 + 因果图 |
| `docs/runtime-structural-reconciliation-20260616.md` | 三维排查 × 代码对账 |
| `docs/runtime-status-report-20260616.md` | 单因果链定界 |
| `docs/incident-runtime-consultation-20260616.md` | 历史诊断 + P1 patch 清单 |

---

## 十四、最终闭合句（会诊结束朗读版）

> **CNexus Runtime 的不稳定，不是执行失败，而是把非确定性认知子系统绑定进同步 ready 布尔门（BDE-1）；Fast/Full 双轨与多路 probe 放大了这一结构错误。SKIP=1 已构成因果证明。Step 1 协议层手术已在工作区落地；会诊任务变为：用新 NSIS 包完成 SKIP 二分，验收 operational 体感，并签字 Step 2 边界。详见 [runtime-deep-consultation-round-20260616.md](runtime-deep-consultation-round-20260616.md)。**

---

**对账人：** Auto（Cursor AI 编码助手）  
**日期：** 2026-06-16
