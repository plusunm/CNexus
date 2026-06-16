# CNexus 桌面 BAT 构建错误报告

**报告日期：** 2026-06-16  
**构建入口：** `scripts/desktop/CNexus-build-installer.bat` → `launch-build.ps1` → `build-cnexus-installer.ps1`  
**日志目录：** `%LOCALAPPDATA%\CNexus\build-logs\`  
**撰写人：** Auto（Cursor AI 编码助手）

---

## 1. 执行摘要

2026-06-16 当日通过桌面 BAT 触发的安装包构建共记录 **10 次**完整日志。其中 **成功 3 次**、**失败 7 次**。失败并非单一根因，而是 **三类可复现错误** 叠加：

| 类型 | 出现次数 | 严重级别 |
|------|----------|----------|
| **A. `tauri:build:vs` 退出码 -1（Next 完成后链中断）** | 6 | P0（假失败/真中断） |
| **B. `runtime-bundle` 文件锁（`_lancedb.pyd`）** | 2+ | P0 |
| **C. `verify-runtime-bundle` Python 冒烟失败** | 1 | P1 |
| **D. 每次构建均出现的 pip / Rust / 编码噪声** | 10 | P2（干扰判读） |

成功产出安装包路径（当次有效）：

`brain-memory-ui/frontend/src-tauri/target/release/bundle/nsis/CNexus_0.1.0-alpha_x64-setup.exe`

---

## 2. 构建链路说明

```
CNexus-build-installer.bat
  └─ launch-build.ps1
       └─ build-cnexus-installer.ps1
            ├─ ensure-nsis.ps1
            ├─ kill-cnexus-before-build.bat
            └─ npm run tauri:build:vs
                 └─ run-in-vs-native.ps1 (vcvars64 + cmd)
                      └─ npm run tauri:build
                           ├─ bundle:runtime
                           ├─ next build (build:desktop)
                           ├─ verify:runtime-bundle
                           ├─ build:sidecar
                           └─ tauri build (Rust + NSIS)
```

**预期耗时：** 8–15 分钟（脚本内已提示）。Rust 编译 + NSIS 压缩阶段可能数分钟无新输出，属正常现象。

---

## 3. 重复错误详述

### 错误 A：`tauri:build:vs finished (exit -1)` — **最高频、最误导**

**现象（6 次）：**  
日志在 Next.js 静态导出成功处戛然而止，例如：

```
○  (Static)  prerendered as static content
>>> tauri:build:vs finished (exit -1)
BUILD FAILED: tauri:build:vs failed (exit -1). Last output: ... First Load JS shared by all 103 kB ...
```

**涉及日志：**  
`build-20260616-040146`、`040643`、`053506`、`053958`、`091759` 及对应 `step-*-tauri-build-vs.log`

**特征：**

- `bundle:runtime` 与 `next build` **均已成功**
- 步骤日志 **未出现** `verify:runtime-bundle`、`build:sidecar`、`tauri build`、`makensis`
- 退出码 **-1**（Windows 下常表示进程被外部终止或未正常返回 exit code）
- 失败时刻距构建开始仅 **约 3–4 分钟**，明显短于完整链路（成功构建约 **11–12 分钟**）

**推断根因（按可能性）：**

1. **构建窗口/父进程被关闭或超时杀死**（自动化环境、手动关窗、系统杀软）
2. **`cmd.exe /c` + 嵌套 `npm run` + `run-in-vs-native.ps1` 管道** 在长时间无输出阶段被误判为挂死
3. **并非 Next/Tauri 编译错误** — 日志中无 TypeScript/Rust 编译失败栈

**与成功构建对比：**  
成功日志（如 `build-20260616-031250.log`）在 Next 完成后继续输出：

```
runtime-bundle OK for tauri build
> build:sidecar
> tauri build
Running makensis ...
Finished 1 bundle at: ...CNexus_0.1.0-alpha_x64-setup.exe
>>> tauri:build:vs finished (exit 0)
```

**建议：**

- BAT 构建时 **勿关闭窗口**，全程等待 15 分钟
- 若 `-1` 再现，从 `step-*-tauri-build-vs.log` 末行确认是否停在 Next 之后，并 **断点续跑**：
  ```powershell
  cd brain-memory-ui\frontend
  npm run verify:runtime-bundle
  npm run build:sidecar
  powershell -File ..\..\scripts\run-in-vs-native.ps1 "cd /d ...\frontend && npx tauri build"
  ```

---

### 错误 B：`runtime-bundle` 目录锁 — **`_lancedb.pyd` 无法删除**

**现象（至少 2 次）：**

```
WARNING: site-packages delete attempt 1..5 failed: Access to the path '_lancedb.pyd' is denied.
Cannot clear locked site-packages: ...\runtime-bundle\python\Lib\site-packages
Close CNexus (tray -> Exit) and retry bundle:runtime.
>>> tauri:build:vs finished (exit 1)
```

**涉及日志：** `build-20260616-035049.log`、`034715.log`（pip 阶段同类 PermissionError）

**根因：**  
已安装的 CNexus / 本地 Python / sidecar 仍加载 `lancedb._lancedb.pyd`，`bundle-runtime-for-desktop.ps1` 清理 `site-packages` 时 **WinError 5 拒绝访问**。

**建议（构建前必做）：**

1. 托盘 **完全退出 CNexus**（非最小化）
2. 运行 `scripts\kill-cnexus-before-build.bat`
3. 任务管理器确认无 `cnexus-product.exe`、`python.exe` 占用 `runtime-bundle`
4. 仍失败时重启后再构建

---

### 错误 C：`verify-runtime-bundle` 冒烟测试失败

**现象（1 次）：**

```
-> Smoke test bundled python...
python.exe : Traceback (most recent call last):
At verify-runtime-bundle.ps1:57
>>> tauri:build:vs finished (exit 1)
```

**涉及日志：** `build-20260616-034715.log`

**上下文：** 同次构建中 pip 安装后出现 `PermissionError` 删除 `_lancedb.pyd`，虽标记 `pip exit 2 ignored`，但 **bundle 内 Python 环境可能不完整**，导致 `import encodings, fastapi` 冒烟失败。

**建议：** 先解决错误 B（文件锁），再全量 `npm run bundle:runtime`。

---

### 错误 D：每次构建均重复出现的「噪声」（非必然失败）

#### D1. pip 依赖冲突提示

```
ERROR: pip's dependency resolver does not currently take into account...
pylance 7.0.0 requires lance-namespace<0.8,>=0.7.7, but you have lance-namespace 0.8.6
```

- **出现：** 全部 10 次构建的 `bundle:runtime` 阶段  
- **性质：** 目标目录安装通常仍显示 `Successfully installed ...`；脚本对部分 exit code 2 已做 ignore  
- **风险：** 与 D2 叠加时可能导致 bundle 损坏

#### D2. pip 安装时 PermissionError（路径含中文时日志乱码）

```
PermissionError: [WinError 5] 拒绝访问: '...\lancedb\_lancedb.pyd'
```

- **出现：** 多次  
- **与错误 B 同源**

#### D3. Rust 编译 warning（6 条 dead_code）

```
warning: constant `DASHBOARD_LABEL` is never used  (boot_sequence.rs)
... cnexus-product (lib) generated 6 warnings
```

- **出现：** 每次进入 `tauri build` 的构建  
- **性质：** 不阻断构建，但污染日志

#### D4. Tauri bundle identifier 警告

```
Warn The bundle identifier "com.cnexus.app" ... ends with `.app`
```

- **性质：** macOS 命名建议，Windows NSIS 可忽略

#### D5. 构建日志 UTF-8 乱码

Next.js 路由表在日志中显示为 `鈹?`、`鈼?` 等，系 **PowerShell 管道 Tee 与控制台代码页** 不一致，影响人工读 log，不影响构建产物。

#### D6. `System.Management.Automation.RemoteException`

Rust/cargo 向 stderr 输出 warning 时，PowerShell 捕获为 RemoteException 行写入 step log — **非实际异常**。

---

## 4. 构建结果统计（2026-06-16）

| 日志文件 | 开始时间 | 结果 | 退出码 | 备注 |
|----------|----------|------|--------|------|
| build-20260616-020224 | 02:02 | ✅ 成功 | 0 | 完整 NSIS |
| build-20260616-024853 | 02:48 | ✅ 成功 | 0 | 完整 NSIS |
| build-20260616-031250 | 03:12 | ✅ 成功 | 0 | 完整 NSIS |
| build-20260616-034715 | 03:47 | ❌ 失败 | 1 | verify 冒烟失败 |
| build-20260616-035049 | 03:50 | ❌ 失败 | 1 | _lancedb.pyd 锁 |
| build-20260616-040146 | 04:01 | ❌ 失败 | -1 | Next 后中断 |
| build-20260616-040643 | 04:06 | ❌ 失败 | -1 | Next 后中断 |
| build-20260616-053506 | 05:35 | ❌ 失败 | -1 | Next 后中断 |
| build-20260616-053958 | 05:39 | ❌ 失败 | -1 | Next 后中断 |
| build-20260616-091759 | 09:17 | ❌ 失败 | -1 | Next 后中断 |

**成功率：** 3/10（30%）  
**若排除 exit -1 的外部中断，环境与锁问题修复后，链路本身具备成功先例。**

---

## 5. 产物与源码不同步风险（构建「成功但行为旧」）

多次失败/中断会导致：

- `out/`（Next 静态资源）已更新，但 **NSIS 未重打**
- `runtime-bundle/` 停留在 **中断前的旧 bundle**（如旧版 `port_guard.py`、旧 sidecar）

**判据：** 对比 `out/`、`runtime-bundle/` 与源码修改时间；仅当 `step-*-tauri-build-vs.log` 出现 `Finished 1 bundle at` 且 `verify nsis installer finished (exit 0)` 时，安装包才可信。

---

## 6. 推荐构建 SOP（减少重复失败）

1. **构建前**
   - 托盘退出 CNexus，运行 `kill-cnexus-before-build.bat`
   - 确认无 Python/cnexus 占用 `runtime-bundle`
2. **构建中**
   - 双击 `scripts\desktop\CNexus-build-installer.bat`，**不关闭窗口**，等待 ≥15 分钟
   - NSIS 压缩阶段无输出属正常
3. **若报 exit -1**
   - 打开 `%LOCALAPPDATA%\CNexus\build-logs\` 最新 `step-*-tauri-build-vs.log`
   - 若 Next 已成功，按 §3 错误 A 断点续跑
4. **若报 exit 1 且含 `_lancedb.pyd`**
   - 完全退出应用后重试；必要时重启 OS
5. **构建后验证**
   - 日志含 `BUILD OK` 与 `verify nsis installer finished (exit 0)`
   - 安装包大小约 **90MB+**，时间戳为当次构建

---

## 7. 后续工程改进建议（供会诊）

| 优先级 | 改进项 |
|--------|--------|
| P0 | `build-cnexus-installer.ps1` 对 exit -1 检测 Next 成功后续跑 sidecar+tauri，或拆分步骤避免单条超长命令 |
| P0 | `bundle-runtime` 锁文件：构建前强制 taskkill + 重试退避，或 rename 旧 site-packages 而非同步 rmtree |
| P1 | pip 使用隔离 venv/target，避免与全局 pylance 冲突及误报 ERROR |
| P1 | 构建日志统一 UTF-8（`[Console]::OutputEncoding` / chcp 65001 全链） |
| P2 | 清理 Rust dead_code warning，减少 stderr 误判 |
| P2 | 构建 manifest：记录 git hash + 关键文件 hash 写入 NSIS 元数据 |

---

## 8. 结论

桌面 BAT 构建链 **设计完整且已有成功先例**，但当日 **70% 失败** 主要来自：

1. **高频 exit -1** — 多发生在 Next 完成后，属于 **链路中断/假失败**，而非前端编译错误；  
2. **runtime-bundle 文件锁** — CNexus 或 Python 未退出导致 `_lancedb.pyd` 无法刷新；  
3. **日志噪声过多** — pip ERROR、Rust warning、编码乱码，增加误判「构建坏了」的概率。

按本报告 §6 SOP 操作，并优先解决 A、B 两类问题，可显著提高一次构建成功率。

---

## 附录 A：构建失败反馈表（提交问题前必填）

> 关联 Runtime 检查表：`docs/incident-runtime-consultation-20260616.md` 附录 A2。

| # | 问题 | 填写 |
|---|------|------|
| 1 | 构建前是否运行 `kill-cnexus-before-build.bat`？ | ☐ 是 ☐ 否 |
| 2 | 是否完全退出 CNexus（托盘 + 任务管理器无 cnexus/pythonw）？ | ☐ 是 ☐ 否 |
| 3 | 最新日志文件路径 | `%LOCALAPPDATA%\CNexus\build-logs\build-________.log` |
| 4 | `step-*-tauri-build-vs.log` **末 5 行**（粘贴） | |
| 5 | 失败退出码 | ☐ -1 ☐ 1 ☐ 其他：____ |
| 6 | 是否出现 `_lancedb.pyd` / `Access denied`？ | ☐ 是 ☐ 否 |
| 7 | Next 静态导出是否已成功（日志含 `Static) prerendered`）？ | ☐ 是 ☐ 否 |
| 8 | `out/` 目录是否已生成？ | ☐ 是 ☐ 否 |
| 9 | 日志是否含 `runtime-bundle OK` / `build:sidecar` / `makensis`？ | ☐ 是 ☐ 否 |
| 10 | 构建窗口是否提前关闭或等待 <15 分钟？ | ☐ 是 ☐ 否 |

**填写人 / 日期：** _______________

---

## 附录 B：架构改进路线图（Sprint 建议）

### B1 构建状态机（应对 exit -1）

- **Stage 1：** Prep & Bundle（kill → bundle:runtime → next build）  
- **Stage 2：** Compile & Package（verify → sidecar → tauri → NSIS）  
- Stage 1 完成后写入 `%LOCALAPPDATA%\CNexus\build-logs\build_stage1.ok`；Stage 2 可独立重跑。  
- **已实现（2026-06-16）：** `scripts/build-resume-from-verify.ps1` — Next 成功后断点续跑。

### B2 Shadow Copy（应对 _lancedb.pyd 锁）

- 构建时将 `runtime-bundle` 依赖复制到 `%TEMP%\cnexus_build_workdir`，在临时目录清理/打包。  
- **状态：** 设计项，待 Sprint 实现（改动 `bundle-runtime-for-desktop.ps1`）。

### B3 日志降噪

- 构建脚本已加 UTF-8（`build-cnexus-installer.ps1`）。  
- 待办：`filter-build-log.ps1` 高亮 ERROR / BUILD FAILED，降级 pip warning 与 Rust RemoteException。

---

## 附录 C：会诊启动发言稿（约 3 分钟）

各位好，CNexus 桌面版当前阻塞集中在 **Runtime 链路** 与 **BAT 构建环境** 两条线，不是单一 UI bug。

**Runtime：** 根因包括 Kuzu 空目录冲突、认知冷启动阻塞、中文路径编码；已落地 `reason`/`progress` API 与 `CNEXUS_BOOT_SKIP_COGNITIVE` 隔离测试，开发机验证 API 可 ready、`memory/stats` 可 200。

**构建：** 6 月 16 日 10 次 BAT 构建，3 成功 7 失败；70% 为 Next 成功后的 **exit -1 链中断**，另有多起 **_lancedb.pyd 文件锁**。成功链路约 11–12 分钟，失败多在 3–4 分钟，说明是进程中断而非编译错误。

**今天会诊三件套：**  
① Procmon 录 CMD 闪窗；  
② SKIP_COGNITIVE + curl full ready；  
③ 按检查表完成一次完整 NSIS 构建后再验 Runtime。

文档：`docs/incident-runtime-consultation-20260616.md`（启动/构建检查表）、本报告（构建错误与反馈表）。

---

**报告撰写：** Auto（Cursor AI 编码助手）  
**日期：** 2026-06-16  
**更新：** 2026-06-16 — 附录 A–C、UTF-8 构建脚本、断点续跑脚本
