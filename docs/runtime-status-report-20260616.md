# CNexus Runtime 冲突 — 工程级事故定界报告（单因果链版）

**汇报日期：** 2026-06-16  
**产品版本：** 0.1.0-alpha  
**验收基线包：** `CNexus_0.1.0-alpha_x64-setup.exe`（2026-06-16 11:04 构建）  
**撰写人：** Auto（Cursor AI 编码助手）  
**受众：** 项目负责人、会诊团队、后续接手开发

---

## 零、一句话定界

> **Runtime 没有稳定进入 `BOOT_4_READY`，但 UI 把 `BOOT_0~3` 的状态噪声（含 `ready_fast`）当成了系统状态来源。**

所有用户可见冲突，均可沿 **一条主因果链** 解释；其余问题均为 **放大器** 或 **验证干扰**，不应再分散排查。

---

## 一、主导失效模式（Single Causal Spine）

### 1.1 症状压缩

| 真实系统状态 | UI 认知状态 | 用户感知 |
|-------------|------------|---------|
| 卡在 `BOOT_2` ~ `BOOT_3`，或相位振荡 | 多源 probe 拼出的「假连续状态」 | 永远在 warming / 假在线 / 偶尔断线 |

### 1.2 唯一主链（P0 — 不要再分散）

```
BOOT_3_COGNITIVE_WARMUP
        ↓
Ollama / embedding / CSE / L3 queue / memory warmup
        ↓
阻塞 · 超时 · 非确定性长尾延迟
        ↓
BOOT_4_READY 未达到（或短暂达到后振荡）
        ↓
evaluate_system_ready() → "warming"（非 "ready"）
        ↓
/v1/system/ready?mode=full 无法稳定返回 status:"ready"
        ↓
前端 runtimeReady=false → canUseRuntimeApi=false → 上传/聊天全禁
```

**代码锚点（后端权威门控）：**

```466:499:core/runtime/boot_protocol.py
def evaluate_system_ready(
    ...
) -> str:
    maybe_advance_cognitive_timeout()
    phase = get_boot_phase()

    if not app_started:
        return "warming"

    if runtime_warming or phase != BootPhase.BOOT_4_READY:
        return "warming"

    if _cognitive_warmup_blocks_ready():
        return "warming"
    ...
    return "ready"
```

**结构性死锁（本质）：**

> 把 **LLM / 认知 warmup** 定义为 **系统 ready 的同步门（Gatekeeper）**，而不是 **能力增强层（Enhancement Layer）**。

在 AI Runtime 上，认知冷启动是 **长尾不确定任务**；当前模型是 **同步 Boot Gate** — UI 请求 ready → 必须等 `BOOT_4_READY` → 否则全部功能关闭。**此设计是 P0 的结构根因。**

---

## 二、放大器（P1 / P2 — 不是根因，但制造「多层都可能有问题」幻觉）

### 2.1 P1：前端多状态源竞态

| 模块 | 行为 | 后果 |
|------|------|------|
| `MindStore` | `probeRuntime`（fast）、`probeRuntimeFull`、`syncRuntimeProbeResult` | 本地 `runtimeReady` / `runtimeReachable` |
| `useFloatRuntimeMonitor` | 独立轮询 fast + full，本地 `phase` 状态 | 与 Store 不同步 |
| `ensureMemoryWriteReady` | 再探 `/v1/memory/stats` | 写入路径第三次判定 |
| `resolveRuntimeConnectionDisplay` | 合成 `isLive` + `monitorPhase` → `canUseRuntimeApi` | 同一系统三套语义 |

```15:75:brain-memory-ui/frontend/lib/runtimeConnection.ts
export function resolveRuntimeConnectionDisplay(input: {
  ...
  monitorPhase?: RuntimeConnectionPhase | null;
}): RuntimeConnectionDisplay {
  ...
  if (isLive && (!monitorPhase || monitorReady)) {
    return { ... canUseRuntimeApi: true, phase: "live" };
  }
  if (isWarming || monitorWarming || (isLive && monitorWarming)) {
    return { ... canUseRuntimeApi: false, phase: "warming" };
  }
```

```25:29:brain-memory-ui/frontend/cnexus-kernel/useMindOverview.ts
  const isLive = effectiveMode === "runtime" && runtimeReady;
  const isWarming = effectiveMode === "runtime" && runtimeReachable && !runtimeReady;
  const canWriteMemory =
    effectiveMode === "demo" || (effectiveMode === "runtime" && runtimeReady);
```

**本质：** 用「局部可达性」拼「系统状态」→ A 见 `ready_fast` 曾显示已连接，B 写入失败显示未连接，C monitor 超时显示 warming。

**当前前端已部分收紧**（`ready_fast` → warming），但 **未实现 SSOT** — 仍在多处主动 probe，而非被动展示后端单一真理。

### 2.2 P2：构建与包不确定性

BAT `exit -1`、`_lancedb.pyd` 文件锁、手动 `build-resume-from-verify.ps1` 续跑。

**本质：** 在调试 **多个版本的 runtime** — 开发机 OK、用户机 ❌、旧包 ❌、新包半成功 ❌。  
**不是 runtime bug**，但 **破坏版本一致性**，使 P0 结论无法稳定复现。

### 2.3 双轨 Ready API（历史假在线来源）

默认 `GET /v1/system/ready`（无 `mode=full`）走 **Fast-Path v1**，返回 `ready_fast` — **不经过** `evaluate_system_ready()`：

```53:54:core/runtime/fast_ready_snapshot.py
    return {
        "status": "ready_fast",
```

Full 路径才走权威判定。前端 `MindStore.probeRuntime` 用 fast，`probeRuntimeFull` / FloatMonitor full 用 `mode=full` — **同一时刻两个端点给出不同「就绪度」**。

---

## 三、关键定性（对「是不是这些问题」的裁决）

| 说法 | 裁决 | 说明 |
|------|------|------|
| 前端门控太严格 | ❌ 非根因 | 门控是后端 `BOOT_4` 语义的下放；收紧是反假在线的 **症状修复** |
| HTTP ready 判断错误 | ⚠️ 半真 | Fast/Full 双轨才是问题；Full 路径逻辑本身与 Boot 一致 |
| UI 状态同步问题 | ❌ 非根因 | P1 放大器；停加 probe 可减噪，不治本 |
| Windows CMD 闪窗 | ❌ 非根因 | 并行 UX 问题，不解释 warming 死循环 |
| Kuzu / 编码 / 存储 | ⚠️ 次因链 | 可阻止到达 `BOOT_2+`；SKIP=1 仍失败时才升 P0 |
| BAT 构建失败 | ❌ 非根因 | P2 交付干扰 |

**✅ 真问题只有一个：**

> **`BOOT_4_READY` 被定义为「必须完成认知 warmup 才算系统启动完成」的同步门，且完成时间不可预测。**

---

## 四、当前系统结构（简图）

```
cnexus-product.exe (Tauri + Next.js)
    │ HTTP/WS → 127.0.0.1:8000
    ▼
cnexus-runtime sidecar (pythonw, CREATE_NO_WINDOW)
    │ -m api.main (brain-memory-ui/api)
    │ CNEXUS_CONTROL_PLANE_ISOLATION=1
    │ CNEXUS_DEPLOY_LEVEL=internal (desktop)
    ▼
Boot Protocol v3
    BOOT_0 → BOOT_1 → BOOT_2 → BOOT_3 → BOOT_4
                              ↑
                    cognitive_warmup_adapter
                    Ollama / embedding / L3 / CSE
    ▼
/v1/system/ready
    default → ready_fast (Fast-Path v1)
    ?mode=full → evaluate_system_ready() → ready | warming
```

**数据目录：** `%LOCALAPPDATA%\CNexus\`（`runtime-bundle/` + `data/`）

---

## 五、代码对账（排查结论）

### 5.1 与用户「单因果链」的对账

| 用户判断 | 代码验证 | 状态 |
|---------|---------|------|
| P0 = Boot 收敛失败 | `phase != BOOT_4_READY` → warming；`_cognitive_warmup_blocks_ready()` 额外挡 | ✅ 一致 |
| P1 = 前端多源竞态 | 4 条独立 probe/门控链并存 | ✅ 一致 |
| P2 = 包版本不一致 | BAT 70% 中断；11:04 包为续跑产物 | ✅ 一致 |
| 修了症状没动结构 | 见 §5.2 | ✅ 一致 |
| SKIP=1 可二分认知阻塞 | `cognitive_disabled()` → 立即 `mark_cognitive_warmup_done(bypass_causal=True)` | ✅ 一致 |

### 5.2 已做修复 vs 未动结构

| 层级 | 已做（症状层） | 未做（结构层） |
|------|---------------|---------------|
| 后端 | `boot_ready_details` reason/progress；UTF-8；Kuzu 路径；memory/stats offload；120s progressive timeout | `ready ≠ full_ready` 拆分；cognitive 改后台非阻塞；`/v1/system/capability` |
| 前端 | `ready_fast` 当 warming；reason 文案；门控与 `runtimeReady` 对齐 | SSOT（废弃本地竞态）；能力向量 UI |
| 交付 | 11:04 NSIS；resume 脚本 | 安装前置清理脚本；BAT stage 化；CI 锁定基线 |

### 5.3 已有但未完成的「渐进」补丁

桌面 sidecar 设 `CNEXUS_DEPLOY_LEVEL=internal`，故 `maybe_advance_cognitive_timeout()` 在 **120s** 后 **可** 强制 `BOOT_4`（personal/internal/dev）：

```198:214:core/runtime/boot_protocol.py
def maybe_advance_cognitive_timeout() -> bool:
    ...
    relaxed = deploy in ("dev", "internal", "personal") or edition == "personal"
    if relaxed:
        return mark_cognitive_warmup_done(bypass_causal=True)
```

**对账结论：** 这是 **超时逃生舱**，不是 **Progressive Capability Model**。用户仍可能在 120s 内长期 warming；若 L3/adapter 逻辑异常，仍可能 **永不收敛**。

### 5.4 开发机 SKIP 通过、用户机失败 — 解释

| 条件 | 预期 |
|------|------|
| `CNEXUS_BOOT_SKIP_COGNITIVE=1` + 新包 | 秒级 `BOOT_4` → **若仍失败，查 API 框架/存储/端口（次因链）** |
| 无 SKIP + Ollama 慢/未起 | 长期 `COGNITIVE_WARMUP` → **P0 主链成立** |
| 旧包 / 脏 `%LOCALAPPDATA%` | 任意结论无效 → **P2 干扰** |

---

## 六、目标系统模型（收敛方向）

### 6.1 当前（错误）

```
UI 请求 ready → 必须 BOOT_4 → 否则全禁
```

### 6.2 应改为 Progressive Capability Model

```
BOOT_0  → API alive          → canProbe
BOOT_1  → memory ok          → canUpload
BOOT_2  → partial cognition  → canChat (degraded)
BOOT_3  → LLM optional       → canReason
BOOT_4  → full ready         → 增强，非 UI 硬门控
```

**UI 依赖能力向量，而非单一状态机：**

```
canChat   = BOOT_1 && memory_ok
canUpload = memory_ok && write_path_ok
canReason = llm_ok
```

---

## 七、最小修复路径（决策用 — 按优先级）

### Step 1（必须）— 拆 ready 权重

```python
# 后端语义
operational_ready = boot >= BOOT_1 and memory_ok   # UI 可基础交互
full_ready = boot_4 and not cognitive_blocks
```

前端 **`canUseRuntimeApi` 绑定 `operational_ready`**，LLM 状态单独展示。

### Step 2（必须）— Cognitive warmup 后台化

```python
# cognitive warmup = background task, NOT boot blocker
start_cognitive_warmup_background()  # 已有，但仍在阻塞 BOOT_4 提交
```

`mark_cognitive_warmup_done` 不应等待 Ollama 全量加载。

### Step 3（必须）— 前端 SSOT

- **停止** 在前端叠加新 probe  
- **废弃** FloatMonitor / MindStore 本地竞态判定  
- 前端 **仅** 渲染 `GET /v1/system/capability`（或统一后的 ready）— **被动显示者**

### Step 4（必须）— 单一权威端点

```
GET /v1/system/capability
```

替代 ready / stats / health 多源；返回：

```json
{
  "status": "booting" | "ready" | "error",
  "capabilities": { "api": true, "memory": true, "chat": false, "llm": false },
  "reason": "COGNITIVE_WARMUP",
  "progress": 65
}
```

语义降级：

- `booting` — 进度条，按能力部分禁用  
- `ready` — API + memory 可用，模型异步预热  
- `error` — 明确错误码，非超时模糊

---

## 八、会诊执行清单（立刻可做）

### 8.1 架构防御（优先）

1. **冻结前端 probe 改动** — 不再加 MindStore/FloatMonitor 逻辑  
2. **后端 SSOT** — 统一 capability 端点设计评审  
3. **语义降级** — `ready` ≠ `full_ready` 写入 RFC/代码

### 8.2 交付强制（消除 P2）

**安装前置脚本（强制）：**

1. 终止 `cnexus-product.exe` 及关联 `python.exe` / `pythonw.exe`  
2. 备份并 **彻底删除** `%LOCALAPPDATA%\CNexus\`  
3. 检查 Ollama：`curl http://127.0.0.1:11434/api/tags` — 未运行则 **脚本报错退出**，不让 Runtime 盲等  

**基线锁定：** 仅 **2026-06-16 11:04** 安装包结论有效；其余视为环境干扰。

### 8.3 取证策略（闭环 — 不看用户口述）

| # | 证据 | 判定 |
|---|------|------|
| 1 | `curl -s http://127.0.0.1:8000/v1/system/ready?mode=full` | 链路是否通；`reason`/`boot_phase` |
| 2 | `%LOCALAPPDATA%\CNexus\data\runtime-api.stderr.log` 末 200 行 | `UnicodeDecodeError` / `PermissionError` / Kuzu |
| 3 | sidecar 环境设 `CNEXUS_BOOT_SKIP_COGNITIVE=1` 冷启 | 秒级 ready → **100% 锁认知冷启动**；仍失败 → **停改前端，查 API/存储** |

### 8.4 分支应对

```
SKIP=1 → ready  within 30s?
    ├─ YES → P0 确认：改 Progressive Capability + 后台 warmup（Step 1–4）
    └─ NO  → 次因链：sidecar 日志 / 端口 / Kuzu / 路径编码
```

---

## 九、为何「修了三天仍冲突」（收敛版）

1. **修的是症状层** — UI probe、timeout、log、reason 字段  
2. **没动结构层** — `BOOT_4` 同步门、cognitive 阻塞 boot、`ready = full readiness`  
3. **验证被 P2 污染** — 多版本 runtime 混测，结论互相否定  
4. **120s 逃生舱不够** — 用户不会在 2 分钟内认为「系统可用」

---

## 十、最终一句话（决策版）

> **CNexus Runtime 的问题不是「没启动」，而是「启动被错误地定义为必须完成 LLM warmup 才算完成」；UI 又在多条 probe 链上放大这一错误定义。**

**下一步不是再加探测，而是：拆门控 → 后台 warmup → 单一 capability 端点 → 基线包 + SKIP 二分取证。**

---

## 附录 A — 相关文档

- `docs/runtime-structural-reconciliation-20260616.md` — **三维排查 + HCRS/DBSM 剖面 · 代码对账（无修复项）**  
- `docs/incident-runtime-consultation-20260616.md` — R1–R8 检查表  
- `docs/desktop-bat-build-errors-report-20260616.md` — 构建失败分析  

---

**汇报人：** Auto（Cursor AI 编码助手）  
**日期：** 2026-06-16
