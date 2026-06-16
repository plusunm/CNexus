# CNexus Runtime 阻塞与 CMD 闪窗 — 会诊执行记录

**日期：** 2026-06-16  
**版本：** 0.1.0-alpha  
**状态：** 因果模型已闭合 → 见 **`docs/runtime-consultation-closure-20260616.md`**（会诊最终对账表）

---

## P0 现场诊断结果

### 1. 接口审计（本机 2026-06-16）

运行 `curl.exe` 探测 `127.0.0.1:8000`：

| 端点 | 结果 |
|------|------|
| `/v1/system/ready?mode=full` | **连接失败**（exit 7 — Runtime 未在运行） |
| `/v1/system/ready` | 连接失败 |
| `/v1/memory/stats` | 连接失败 |

**结论：** 诊断时 API 未监听 8000 端口。需在 CNexus 启动后 30–120 秒内重跑上述命令，或先手动启动 sidecar。

**会诊复现命令（PowerShell）：**

```powershell
curl.exe -s --max-time 10 "http://127.0.0.1:8000/v1/system/ready?mode=full"
curl.exe -s --max-time 10 "http://127.0.0.1:8000/v1/system/ready"
curl.exe -s --max-time 10 "http://127.0.0.1:8000/v1/memory/stats"
```

### 2. 日志证据（历史 `%LOCALAPPDATA%\CNexus\data\`）

| 信号 | 含义 |
|------|------|
| `EventLoopOffloadTimeout: offload exceeded 30.0s` | CSE live 路径阻塞 offload 线程池 |
| `UnicodeDecodeError: 'gbk' codec...` | 子进程 stdout 未按 UTF-8 解码 |
| `Kuzu unavailable ... kuzu_db` | **Sidecar 预创建空目录 + Python mkdir**，Kuzu 无法在该路径初始化 |

### 3. CMD 闪窗（Procmon — 待会诊现场）

**过滤规则：** `Process Name is cmd.exe OR powershell.exe`，启用 Parent Process 列。

**源码已消除的路径：** PowerShell port_guard 循环、Tauri preflight/cleanup PowerShell、sidecar `pythonw.exe` + `CREATE_NO_WINDOW`。

**仍须 Procmon 确认的：** 第三方 Ollama、杀毒、未更新 bundle 中的旧 sidecar。

---

## P1 已实施代码修复（2026-06-16）

### 1. Kuzu 路径（根因修复）

| 文件 | 改动 |
|------|------|
| `cnexus-runtime-sidecar/src/main.rs` | 不再预创建 `kuzu_db` 目录 |
| `storage/graph.py` | 仅创建父目录；移除空 `kuzu_db` 目录后再交给 Kuzu |
| `core/paths.py` | 新增 `ensure_runtime_data_dirs()` |
| `brain-memory-ui/api/deps.py` | Runtime 初始化前调用目录规范化 |

### 2. 编码硬化

| 文件 | 改动 |
|------|------|
| `core/windows_subprocess.py` | 默认 `encoding=utf-8`, `errors=replace`；`utf8_subprocess_env()` |
| `core/ollama_manager.py` | Popen 注入 `PYTHONIOENCODING` / `PYTHONUTF8` |
| sidecar `main.rs` | 环境变量 `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1` |

### 3. 就绪状态机外显

| 文件 | 改动 |
|------|------|
| `core/runtime/boot_protocol.py` | `boot_ready_details()` → `ready`, `reason`, `progress` |
| `api/system_ready.py` | full/warming 响应携带上述字段 |

**reason 枚举示例：** `API_STARTING`, `RUNTIME_INIT`, `COGNITIVE_WARMUP`, `L3_QUEUE_DRAIN`, `COGNITIVE_WARMUP_TIMEOUT`

### 4. 认知隔离与渐进就绪

| 环境变量 | 作用 |
|----------|------|
| `CNEXUS_BOOT_SKIP_COGNITIVE=1` | 跳过认知 warmup，用于 P0 阻塞源验证 |
| （内置）personal/internal 版 | 认知 warmup 超时后 **progressive ready** → `BOOT_4` |

### 5. CSE 超时降级

| 文件 | 改动 |
|------|------|
| `brain-memory-ui/api/routes/cse.py` | 使用 `CNEXUS_OFFLOAD_TIMEOUT_SEC`（默认 120s）；超时返回 **503 + reason** 而非 500 |

---

## 会诊 120 分钟路线图（执行清单）

| 阶段 | 时间 | 动作 | 通过标准 |
|------|------|------|----------|
| I | 0–30 min | Procmon 录启动 20s | 定位每个 cmd/powershell 的 Parent + Command Line |
| II | 30–70 min | 设 `CNEXUS_BOOT_SKIP_COGNITIVE=1` 重启 | full ready ≤ 3s 且 `reason=null` |
| III | 70–100 min | 中文路径下检查 `kuzu_db` 非空目录 | stderr 无 Kuzu path error |
| IV | 100–120 min | 决策：UI 展示 `reason`/`progress` | 用户可见「正在加载模型…」而非笼统「正在启动」 |

---

## 验证步骤（修复后）

1. 删除 `%LOCALAPPDATA%\CNexus\data\kuzu_db`（若为空目录）
2. 重新打包安装：`npm run build:installer`
3. 启动后执行 P0 curl 三连
4. 期望 full ready JSON 含 `"ready": true` 或 `"reason": "COGNITIVE_WARMUP"` + `progress`
5. Procmon 确认无持续 cmd 闪窗

---

## 交付物状态

| 交付物 | 状态 |
|--------|------|
| 故障树（Kuzu 空目录 + cognitive 阻塞） | ✅ 本文档 |
| `reason`/`progress` API | ✅ 已代码化 |
| UI `useRuntimeStatus` 消费 reason | ✅ 已代码化 |
| 中文路径无 CMD 录屏 | ⏳ 待重装后 Procmon 验证 |
| BAT 构建错误报告 | ✅ `docs/desktop-bat-build-errors-report-20260616.md` |

---

## 附录 A：启动与构建强制检查表（会诊团队必用）

> **两大核心矛盾：**  
> ① **Runtime 链路阻塞** — API 未监听 / 就绪门控过严 / 认知冷启动占用；  
> ② **Build 环境污染** — 文件锁、进程残留、构建链 exit -1 中断导致旧 bundle 混入新包。  
> 会诊前必须按本表逐项勾选，**未勾满不得宣称「已验证修复」**。

### A1. Runtime 启动检查表（每次测 Runtime 前）

| # | 检查项 | 命令 / 动作 | 通过标准 |
|---|--------|-------------|----------|
| R1 | 数据目录清理 | 删除 `%LOCALAPPDATA%\CNexus\data\kuzu_db`（若为空目录） | 目录不存在或含 Kuzu 数据文件 |
| R2 | 盲启动隔离 | `set CNEXUS_BOOT_SKIP_COGNITIVE=1` 后启动 API | 3–10s 内 full ready |
| R3 | 端口监听 | `curl.exe -s http://127.0.0.1:8000/v1/health` | 返回 `"status":"ok"` |
| R4 | Full ready | `curl.exe -s ".../v1/system/ready?mode=full"` | `status: ready` 或带 `reason`+`progress` |
| R5 | 写入路径 | `curl.exe -s ".../v1/memory/stats"` | HTTP 200 JSON，非 500 |
| R6 | 认知全路径 | **去掉** SKIP_COGNITIVE，冷启动一次 | 120s 内 ready 或 UI 显示具体 reason |
| R7 | CMD 闪窗 | Procmon 过滤 cmd/powershell，录启动 20s | 无持续闪窗；记录 Parent+CommandLine |
| R8 | 日志 | 查看 `runtime-api.stderr.log` 尾部 | 无 Kuzu path error、无 GBK UnicodeDecodeError |

**开发环境手动启动 API（会诊复现）：**

```powershell
$repo = "D:\类脑记忆\CNexus — Observational Cognition Platform"
$ui = Join-Path $repo "brain-memory-ui"
$env:PYTHONPATH = "$ui;$repo"
$env:CNEXUS_BOOT_SKIP_COGNITIVE = "1"
$env:BM_MEMORY_DIR = "$env:LOCALAPPDATA\CNexus\data"
$env:BRAIN_MEMORY_ROOT = $ui
$env:CNEXUS_AUTO_RUNTIME_WARM = "1"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $ui
python -m api.main
```

**2026-06-16 开发机验证记录（SKIP_COGNITIVE=1）：**

| 检查项 | 结果 |
|--------|------|
| R3 health | ✅ ok |
| R4 full ready | ✅ `boot_4_ready`，约 8s |
| R5 memory/stats | ✅ 200（修复 asyncio.run 后） |
| reason/progress | ✅ warming 时 `RUNTIME_INIT (25%)` → ready 时 `progress: 100` |

---

### A2. 桌面 BAT 构建检查表（每次打安装包前）

| # | 检查项 | 命令 / 动作 | 通过标准 |
|---|--------|-------------|----------|
| B1 | 完全退出应用 | 托盘 → 退出；任务管理器无 cnexus/pythonw | 无 CNexus 相关进程 |
| B2 | 构建前杀进程 | `scripts\kill-cnexus-before-build.bat` | 输出 `:8000, :3000 released` |
| B3 | 文件锁检查 | 确认无 `_lancedb.pyd` 占用（Resource Monitor） | 可删除 `runtime-bundle\...\site-packages` |
| B4 | 编码环境 | sidecar / 构建脚本含 `PYTHONUTF8=1` | 日志可读、少乱码 |
| B5 | 启动 BAT | `scripts\desktop\CNexus-build-installer.bat` | **不关闭窗口 ≥15 分钟** |
| B6 | 阶段完整性 | 打开最新 `step-*-tauri-build-vs.log` | 含 `runtime-bundle OK`、`build:sidecar`、`makensis`、`Finished 1 bundle` |
| B7 | 退出码 | 主日志末尾 | `BUILD OK` + `verify nsis installer finished (exit 0)` |
| B8 | 产物 | NSIS 路径 | `CNexus_0.1.0-alpha_x64-setup.exe` ≥90MB，时间戳为当次 |
| B9 | 源码同步 | 对比 `out/`、`runtime-bundle/` 与源码 mtime | 不早于当次 `bundle:runtime` |
| B10 | exit -1 续跑 | 若 Next 成功但 exit -1 | 手动：`verify:runtime-bundle` → `build:sidecar` → `tauri build` |

**构建失败分类速查：**

| 退出码 / 关键字 | 类型 | 首要动作 |
|-----------------|------|----------|
| `exit -1`，日志停在 Next 静态导出后 | 链中断（非编译错） | B10 断点续跑；查是否关窗/超时/杀软 |
| `_lancedb.pyd` / `Access denied` | 文件锁 | B1–B3 重做，必要时重启 OS |
| `verify-runtime-bundle` / Traceback | bundle 损坏 | 全量 `npm run bundle:runtime` |
| pip `lance-namespace` ERROR | 噪声（通常） | 若 B6 通过可忽略；否则配合 B3 |

详细统计与日志文件名见：**`docs/desktop-bat-build-errors-report-20260616.md`**（撰写：Auto，2026-06-16）。

---

### A3. 会诊 120 分钟 ↔ 检查表映射

| 路线图阶段 | 对应检查项 | 决策点 |
|------------|------------|--------|
| I Procmon 闪窗 | R7 | 代码 vs 第三方 Ollama |
| II SKIP_COGNITIVE | R2、R4 | 阻塞在认知冷启动 → 渐进就绪 |
| III Kuzu/路径 | R1、R8 日志 | 中文路径 → ProgramData hash |
| IV UI reason | R4 JSON + 前端 | 停止堆叠 probe |
| （并行）稳定安装包 | A2 全表 | 无 BUILD OK 不做 Runtime 验收 |

---

### A4. 禁止事项（会诊期间）

1. **禁止**在未完成 B6–B8 的情况下，用旧安装包验证 Runtime 修复。  
2. **禁止**在前端新增独立 probe 链；仅消费 `/v1/system/ready` 的 `reason`/`progress`。  
3. **禁止**将 pip `lance-namespace` ERROR  alone 判为构建失败（须看 B6 是否完整）。  
4. **禁止**将 Next.js 成功后的 `exit -1` 判为 TypeScript 编译错误（须查 B10）。

---

**检查表维护：** Auto（Cursor AI 编码助手）  
**关联文档：**

- `docs/desktop-bat-build-errors-report-20260616.md` — BAT 构建 10 次日志分析  
- `docs/incident-runtime-consultation-20260616.md` — 本文档

---

## 附录 B：会诊开场白（约 5 分钟，建议宣读）

> 用途：统一会诊认知，禁止即兴调试。宣读后可按附录 A 检查表逐项执行。

---

各位好，我是 CNexus 桌面版本轮问题的主责执行方。今天 **120 分钟** 的目标不是「碰运气让软件启动一次」，而是 **消灭随机性**——用可复现的证据链，把 Runtime 阻塞和 CMD 闪窗两类问题定责、定修复、定验收。

### 一、我们面对的两条矛盾（30 秒）

第一，**Runtime 链路阻塞**：API 可能未监听 8000，或进程在跑但 boot 门控未进 `ready`，用户看到「正在启动」却无法上传、聊天。  
第二，**Build 环境污染**：BAT 构建 10 次里 7 次失败，多为 Next 成功后的 **exit -1** 和 **`_lancedb.pyd` 文件锁**，导致 `runtime-bundle` 残留旧代码——**用旧包验证新修复，等于白修三天**。

今天所有验收，必须基于 **curl JSON**、**构建日志 exit 0** 或 **Procmon 进程链**，不接受「感觉好像快了一点」的体感反馈。

### 二、已完成的工程准备（1 分钟）

代码侧 P1 已落地，包括但不限于：

- Kuzu：sidecar 不再预建空 `kuzu_db` 目录；Python 侧路径规范化  
- 编码：UTF-8 注入 sidecar / subprocess，缓解 GBK `UnicodeDecodeError`  
- 就绪外显：`/v1/system/ready` 返回 **`ready` / `reason` / `progress`**  
- 隔离测试：**`CNEXUS_BOOT_SKIP_COGNITIVE=1`** 可在开发机 8–10 秒内 full ready  
- UI：前端 **`useRuntimeStatus`** 已对接 reason 文案，不再堆叠 probe  
- 构建：`build-cnexus-installer.ps1` UTF-8；**`build-resume-from-verify.ps1`** 应对 exit -1 断点续跑  

开发机 SKIP 模式下 **health / full ready / memory/stats 均已通过**。桌面安装包仍需在本轮用 **新 NSIS + 干净数据目录** 复验。

### 三、今天 120 分钟的四段任务（2 分钟）

| 时段 | 任务 | 通过标准 |
|------|------|----------|
| **0–30 min** | Procmon 录启动 20–60s | 每个 cmd/powershell 有 Parent + Command Line；区分 CNexus vs Ollama/杀毒 |
| **30–70 min** | `SKIP_COGNITIVE=1` + curl 三连 | 3–10s 内 full ready；JSON 含 reason/progress |
| **70–100 min** | 去 SKIP，冷启动 + Kuzu | stderr 无 Kuzu path error；中文路径下数据目录正常 |
| **100–120 min** | UI + 上传/聊天 | warming 显示具体文案（如「正在加载认知引擎 (45%)…」），非笼统「正在启动」 |

**并行约束：** 凡 Runtime 验证，必须先过 **附录 A2 构建检查表 B7**——日志含 **`BUILD OK`** 且 **`verify nsis installer finished (exit 0)`**。无 BUILD OK，**禁止**用该安装包做 Runtime 验收。

### 四、三条执行纪律（1 分钟）

1. **拒绝体感反馈** — 只认 curl JSON、Procmon、stderr 关键字。  
2. **强制构建一致性** — 构建失败先填 **`desktop-bat-build-errors-report` 附录 A 反馈表**，再讨论 Runtime。  
3. **UI 与后端对齐** — reason/progress 准确后，前端微文案必须绑定；这是减少用户焦虑的「最后一公里」。

### 五、三个诊断判据（30 秒）

- **闪窗：** Procmon 中若 cmd 的 Parent 为 CNexus 相关进程 → 代码路径未覆盖，继续改 sidecar/subprocess；若 Parent 为 Ollama 第三方 → 单独定责。  
- **阻塞：** SKIP 下 3 秒内 ready → 主瓶颈在 **认知/Ollama 冷启动**，共识 **渐进就绪**，API 先活、模型异步 warmup。  
- **构建：** 见 `_lancedb.pyd` 拒绝访问 → **立即停止重试**，执行 `kill-cnexus-before-build.bat`，必要时重启 OS，**禁止**在锁文件环境下反复 bundle。

### 六、开场后立即动作（30 秒）

1. 指定一人打开 `%LOCALAPPDATA%\CNexus\build-logs\` 与 `runtime-api.stderr.log`  
2. 指定一人准备 Procmon 过滤规则（见附录 A1 R7）  
3. 若尚无当次安装包 → 按 A2 启动 BAT 构建，**窗口不关，≥15 分钟**  
4. 构建成功后，全员切换附录 A1 R1–R8

---

**文档入口：**

- 本文件附录 A — 启动与构建强制检查表  
- `docs/desktop-bat-build-errors-report-20260616.md` — 构建失败模式与反馈表  

有问题按检查表编号提问（例如「R4 不过」「B6 缺 makensis」），避免散点调试。

**谢谢。我们开始按表执行。**

---

**撰写：** Auto（Cursor AI 编码助手）  
**日期：** 2026-06-16

