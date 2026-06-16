# CNexus Runtime — 深度会诊（第一轮执行手册）

**会诊日期：** 2026-06-16  
**产品版本：** 0.1.0-alpha  
**会诊性质：** 架构纠错阶段 — **证据闭合 + 现场二分 + 新包验收**  
**依据文档：** 四份对账链（见 §一）  
**撰写人：** Auto（Cursor AI 编码助手）

---

## 〇、会诊目标（只答三个问题）

本轮 **不** 再讨论「是不是前端 bug」「是不是构建问题」——四份文档已闭合因果。

会诊只产出三个可执行答案：

| # | 问题 | 合格输出 |
|---|------|---------|
| Q1 | P0 仍是 BDE-1，还是并列 P0'（IO/打包）？ | SKIP=1 二分结论（A/B） |
| Q2 | Step 1 手术是否达到「用户可感知」？ | operational 后 chat 可用、upload 绑定 full 的实测 |
| Q3 | 下一轮架构边界画在哪？ | 签字：认知是否永久退出 full gate / upload 是否可渐进 |

---

## 一、四份文档分工（会诊资料地图）

```text
runtime-status-report          → 单因果链定界（给所有人 5 分钟读）
runtime-structural-reconciliation → 三维排查 × 代码对账（技术员随身）
runtime-engineering-verdict    → 前因后果 + BDE-1 判决（主持人白板）
runtime-consultation-closure   → 120 分钟执行表 + 决策 A/B（本场剧本）
```

| 文档 | 回答什么 | 本场谁用 |
|------|---------|---------|
| [status-report](runtime-status-report-20260616.md) | P0/P1/P2 分层、F1–F3 | 开场定界 |
| [structural-reconciliation](runtime-structural-reconciliation-20260616.md) | 环境/协议/UI 对账表 | 现场技术员 |
| [engineering-verdict](runtime-engineering-verdict-20260616.md) | 前因→机制→后果、因果图 | 架构决策 |
| [consultation-closure](runtime-consultation-closure-20260616.md) | 执行表、禁语、日志路径 | **本场主脚本** |

---

## 二、已闭合 vs 待证（会诊前必读）

### 2.1 已闭合（静态 + 实验，不可再争论）

| ID | 结论 |
|----|------|
| **BDE-1** | `ready` = 全子系统 AND；认知 warmup 绑进 `BOOT_4` 语义门 |
| **F1** | `BOOT_4` 是组合门，不是阶段名 |
| **F2** | Fast/Full = Dual Reality（历史）；Step 1 已用 capability 收敛 |
| **F3** | SKIP=1 ablation 在开发机成立 → cognitive 是控制点 |
| **P1** | 多 probe 放大；Step 1 已收敛到 `syncSystemCapability` SSOT |
| **P2** | 旧包/脏数据/ BAT exit -1 污染结论 |

### 2.2 源码进展（相对 closure §八「Step 1 未开工」已更新）

| Step | closure 记录 | **当前工作区** |
|------|-------------|----------------|
| operational / full 拆分 | ❌ | ✅ `evaluate_operational_ready()` + capability payload |
| `/v1/system/capability` | ❌ | ✅ 已实现 |
| 前端 SSOT | ❌ | ✅ `MindStore.syncSystemCapability`；FloatMonitor 单源 |
| cognitive 不挡 operational | ❌ | ✅ **语义层** operational 可不等待 BOOT_4 |
| cognitive 不挡 full | — | ❌ `evaluate_system_ready()` 仍要求 BOOT_4 |
| 冲突监控日志入包 | — | ✅ bundle 模板 + NSIS + `conflict_monitor` |

**会诊含义：** 问题定义已闭合；**验收对象变为「新安装包 + 现场证据」**，不是继续写对账。

### 2.3 待证（本场必须填表）

- [ ] 新 NSIS 包路径与构建时间戳  
- [ ] 清 `%LOCALAPPDATA%\CNexus` 后冷启  
- [ ] curl capability + full + conflict_log  
- [ ] SKIP=1 用户机 ≤30s  
- [ ] 无 SKIP：operational 时刻 vs full 时刻（秒）  
- [ ] UI：chat 在 operational 后可用；upload 在 full 前禁用提示正确  
- [ ] `runtime-conflict-monitor.log` 有 `CAPABILITY_STATE` / 无异常 `DUAL_REALITY_*`

---

## 三、会诊角色与分工

| 角色 | 职责 | 产出 |
|------|------|------|
| **主持人** | 守议程、禁语、决策 A/B | 会诊记录签字 |
| **技术员** | curl、环境清理、SKIP 环境变量 | §七 取证表 |
| **开发** | 读 conflict_log、stderr、capability JSON | §七 技术附录 |
| **产品/决策** | Q3：upload 是否必须等 full | §八 架构边界 |

---

## 四、120 分钟议程（主脚本）

### Phase 0 · 定界（0–10 min）

**朗读（closure §十四）：**

> 不稳定来自 BDE-1：认知 warmup 绑进同步 ready 门；Dual Reality 与多 probe 曾放大该错误。会诊任务：现场二分 + 验收 Step 1 新包。

**动作：**

1. 确认安装包为 **本轮构建产物**（非 11:04 旧基线，除非明确对比）  
2. `Remove-Item -Recurse -Force "$env:LOCALAPPDATA\CNexus" -ErrorAction SilentlyContinue`  
3. 安装 → 启动 CNexus → 等待 30s

---

### Phase I · 链路取证（10–40 min）

**PowerShell 脚本（按序执行，结果填入 §七）：**

```powershell
$base = "http://127.0.0.1:8000"
curl.exe -s --max-time 15 "$base/v1/system/capability"
curl.exe -s --max-time 15 "$base/v1/system/ready?mode=full"
curl.exe -s --max-time 15 "$base/v1/memory/stats"
curl.exe -s --max-time 15 "$base/v1/system/conflict_log?tail=50"
Get-Content "$env:LOCALAPPDATA\CNexus\data\runtime-conflict-monitor.log" -Tail 30 -ErrorAction SilentlyContinue
Get-Content "$env:LOCALAPPDATA\CNexus\data\runtime-api.stderr.log" -Tail 30 -ErrorAction SilentlyContinue
```

**判读速查：**

| 观测 | 含义 |
|------|------|
| capability 无响应 | P0'：sidecar/API 未 listen |
| `operational_ready:true` 且 `full_ready:false` 且 `reason:COGNITIVE_WARMUP` | **BDE-1 预期态**（Step 1 生效） |
| `operational_ready:false` 长期 | runtime warm / memory / IO → 查 stderr |
| conflict_log 含 `DUAL_REALITY_FAST_NOT_OPERATIONAL` | Dual Reality 残留，需查是否旧前端/旧包 |
| `RUNTIME_WARM_FAILED` | P0' 并列 |

---

### Phase II · SKIP 二分（40–70 min）——**全场最关键**

**目的：** 证明或否定「cognitive gate 是唯一主阻塞」。

1. 完全退出 CNexus（托盘 Exit）  
2. 设置环境（sidecar 继承用户/系统环境，或写入快捷启动脚本测试）：

```powershell
[System.Environment]::SetEnvironmentVariable("CNEXUS_BOOT_SKIP_COGNITIVE", "1", "User")
```

3. 重启 CNexus，30s 后：

```powershell
curl.exe -s --max-time 15 "http://127.0.0.1:8000/v1/system/ready?mode=full"
curl.exe -s --max-time 15 "http://127.0.0.1:8000/v1/system/capability"
```

| 结果 | 裁定 |
|------|------|
| full `ready` / `full_ready:true` **≤30s** | **决策 A**：BDE-1 定案；Step 1 验收 + 规划 Step 2（cognitive 永久后台化） |
| 仍失败 / 无 8000 | **决策 B**：暂停 readiness 手术；Procmon + stderr + sidecar exit |

**会后恢复：**

```powershell
[System.Environment]::SetEnvironmentVariable("CNEXUS_BOOT_SKIP_COGNITIVE", $null, "User")
```

---

### Phase III · 无 SKIP 体感曲线（70–95 min）

1. 清除 SKIP，冷启  
2. 每 10s 记录一次（共 12 次 ≈ 2 min，必要时延至 120s）：

```powershell
curl.exe -s --max-time 10 "http://127.0.0.1:8000/v1/system/capability" |
  ConvertFrom-Json |
  Select-Object status, operational_ready, full_ready, cognitive_status, reason, progress
```

3. 同步 UI 观察：

| 时刻 | 期望（Step 1 设计） |
|------|---------------------|
| operational 后 | 侧栏/悬浮窗「上线」或等价；**可进入聊天** |
| full 前 | 上传按钮禁用或提示「认知索引构建中」 |
| full 后 | 上传可用 |

**若 operational 后仍全禁：** Step 1 前端未随新包生效 → P2 交付问题，非 BDE-1 推翻。

---

### Phase IV · 架构决策（95–120 min）

仅讨论 **§八** 三项，禁止新 patch 提议。

---

## 五、决策树（会诊终裁）

```text
                    启动 CNexus
                         │
            ┌────────────┴────────────┐
            │ 8000 无响应？            │
            └────────────┬────────────┘
                    YES → 【B】P0' IO/打包/sidecar
                    NO
                         │
            ┌────────────┴────────────┐
            │ SKIP=1 → full ≤30s？    │
            └────────────┬────────────┘
                 NO → 【B】P0'
                 YES → 【A】BDE-1 定案
                         │
            ┌────────────┴────────────┐
            │ 无 SKIP：operational      │
            │ 后 UI 可 chat？           │
            └────────────┬────────────┘
                 NO → 【交付/前端未更新】重装新包
                 YES → Step 1 用户体感 PASS
                         │
            ┌────────────┴────────────┐
            │ full 平均 >120s？       │
            └────────────┬────────────┘
                 YES → 批准 Step 2：cognitive 永不挡 operational；upload 策略签字
                 NO  → 监控即可，减少 120s bypass 依赖
```

---

## 六、会诊禁语 / 必用语（强制执行）

| 禁语 | 替换 |
|------|------|
| 「再加轮询」 | 「看 conflict_log / capability」 |
| 「调大 timeout」 | 「拆 operational / full」 |
| 「ready_fast 算在线」 | 「operational_ready」 |
| 「BOOT_4 写错了」 | 「BDE-1 门控公理」 |

**必用语：** BDE-1 · operational_ready · full_ready · capability SSOT · conflict_log

---

## 七、现场取证表（打印填写）

**环境**

| 项 | 填写 |
|----|------|
| 安装包路径 | |
| 构建时间 | |
| 已清 LocalAppData | ☐ |
| Ollama 运行 | ☐ 是 ☐ 否 |

**Phase I — capability 首次（T+30s）**

```json
（粘贴 capability JSON）
```

| 字段 | 值 |
|------|-----|
| operational_ready | |
| full_ready | |
| ready_for_chat | |
| ready_for_upload | |
| reason | |
| boot_phase | |

**Phase II — SKIP=1**

| 项 | 值 |
|----|-----|
| 冷启到 full_ready 秒数 | |
| 裁定 A / B | |

**Phase III — 无 SKIP 时间线**

| T+s | operational | full | reason |
|-----|-------------|------|--------|
| 10 | | | |
| 20 | | | |
| 30 | | | |
| 60 | | | |
| 120 | | | |

**UI**

| 项 | PASS/FAIL |
|----|-----------|
| operational 后可聊天 | |
| full 前上传有明确提示 | |
| full 后上传成功 | |
| 无 ready/offline 剧烈抖动 | |

**日志**

| 文件 | 异常行（如有） |
|------|---------------|
| runtime-conflict-monitor.log | |
| runtime-api.stderr.log | |

---

## 八、架构决策签字栏（Phase IV）

| 决策项 | 选项 | 签字 |
|--------|------|------|
| **D1** cognitive 是否永久退出 operational gate | ☐ 是（推荐） ☐ 否 | |
| **D2** upload 门控 | ☐ 仅 full_ready ☐ operational+memory 即可 | |
| **D3** 120s bypass | ☐ 保留逃生 ☐ 降级为日志-only | |
| **D4** 下轮交付基线 | ☐ 本轮新 NSIS ☐ 其他：____ | |

---

## 九、会诊结论模板（结束时填写）

### 9.1 主因裁定

☐ **A — BDE-1 定案**（SKIP 通过 + operational 体感符合设计）  
☐ **B — P0' 并列**（SKIP 失败或 API 不稳）  
☐ **C — 交付未生效**（代码有、包/前端旧）

### 9.2 用户体感（一句话）

> _________________________________________________

### 9.3 下一步（仅选已签字项）

- [ ] 发布本轮 NSIS 为唯一验收基线  
- [ ] Step 2：cognitive 后台化，full 仅影响 upload/增强能力  
- [ ] P0' 排查：Procmon / Kuzu / sidecar  
- [ ] 禁止：新增 probe、仅改 timeout

---

## 十、主持人开场白（3 分钟）

各位，今天不是来「找 bug」的。四份文档已经把因果闭合了：

**CNexus 的问题，是稳定性定义错了**——我们把非确定性的认知子系统，绑进了同步的 `ready` 布尔门（BDE-1）。历史上 Fast/Full 双轨和多路 probe 放大了这个问题。

源码里已经做了 Step 1：operational 与 full 拆分、capability 端点、冲突监控日志入包。今天只做三件事：SKIP 二分、无 SKIP 体感曲线、对 Step 1 做用户级验收。

请不要讨论「再加轮询」或「调 timeout」。请把结果写进取证表和 conflict_log。

---

## 十一、与会后 24h 交付物

| 交付物 | 负责人 |
|--------|--------|
| 填完的 §七 取证表 | 技术员 |
| §九 签字结论 | 主持人 |
| conflict_log + stderr 附件 | 开发 |
| 若 A：Step 2 RFC（1 页） | 架构 |

---

**撰写人：** Auto（Cursor AI 编码助手）  
**日期：** 2026-06-16
