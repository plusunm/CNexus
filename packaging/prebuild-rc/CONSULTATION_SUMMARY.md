# CNexus + Runtime 打包前准备工作 — 会诊式总结

**Release Candidate · 0.1.0-alpha · Tauri 双进程桌面安装包**

本文整合：悬浮窗稳定性、孤儿进程、启动状态机、Runtime 契约、加壳风险等前期讨论，形成**打包前唯一入口文档**。

---

## 架构不变量

```text
CNexus_Setup.exe
├── CNexus.exe                 # 进程 1：Tauri WebView UI（float + dashboard）
├── cnexus-runtime.exe         # 进程 2：Sidecar 启动器
└── resources/runtime-bundle/
    ├── python/python(w).exe   # 进程 3：python -m api.main @ 127.0.0.1:8000
    └── app/                   # API 薄层 + config
```

通信：**仅** [RUNTIME_CONTRACT.md](../../brain-memory-ui/docs/RUNTIME_CONTRACT.md) 所列 REST/WS。

---

## 1️⃣ 代码与依赖准备

| 项 | CNexus 现状 | 打包前要求 |
|----|-------------|------------|
| 调试日志 | Rust 有 `eprintln!`（sidecar/启动）；Python stdout 已 null | Release 可接受文件日志后续补；**禁止** inherit 控制台 |
| Feature flag | `CNEXUS_TAURI=1` 控制 Next export | 构建 desktop 必须带此变量 |
| `Cargo.lock` | `src-tauri/Cargo.lock` + sidecar 独立 lock | 提交 lock，构建用 `--locked` 可选 |
| `package-lock.json` | 存在 | `npm ci` 可复现 |
| 单元/契约测试 | `test:demo` · `test:kernel-boundary` | 审计脚本自动跑 |
| 前端资源 | `frontendDist: ../out` | `out/desktop.html` + `_next/static` |
| 路径 | Sidecar 用 exe 旁 `resources/runtime-bundle`；数据 `%LOCALAPPDATA%\CNexus` | **禁止** 写死 repo 相对路径进 Release |
| 版本号 | `VERSION` ↔ package/Cargo/tauri/pyproject/health | 审计脚本逐项比对 |

**结论：** 契约与 kernel 边界测试已通过；**打包前须重新** `build:desktop` 生成 `out/` 与 `runtime-bundle/`。

---

## 2️⃣ 多进程管理检查

| 项 | 实现位置 | 状态 |
|----|----------|------|
| UI 启动 Runtime | `runtime_sidecar.rs` → `shell().sidecar("cnexus-runtime")` | ✅ |
| 绑定 127.0.0.1 | `BM_API_PORT=8000`，FastAPI 本地 | ✅ 契约冻结 |
| 动态端口 | 未实现 | ⚠️ RC 固定 8000；占用时需人工 `kill-cnexus-runtime` |
| 正常退出 UI → Runtime 停 | `RunEvent::Exit` + tray quit + `stop_runtime_sidecar` | ✅ 需**新安装包** |
| Python 随 Sidecar 退出 | Windows Job Object + `taskkill /T` | ✅ |
| pythonw + 无 CMD | `cnexus-runtime-sidecar` + `CREATE_NO_WINDOW` | ✅ 需新 sidecar 构建 |
| UI 强杀 → Runtime 自杀 | 无父进程心跳 | ⚠️ 见 [KNOWN_GAPS.md](./KNOWN_GAPS.md) |
| 卸载清进程 | `windows/hooks.nsh` + pythonw + :8000 | ✅ |
| 启动顺序 | `boot_sequence` → `cnexus:runtime-ready` → `DesktopFloatBoot` → show | ✅ |
| 悬浮窗 | 360×228 · hidden until ready · 可拖动 | ✅ |

**残留进程验收：** 托盘「退出 CNexus」→ `tasklist` 无 `cnexus-runtime` / `api.main` python → `:8000` 不通。

---

## 3️⃣ 配置与环境检查

| 配置 | 文件 | 要点 |
|------|------|------|
| Float 窗口 | `tauri.conf.json` | 360×228 · decorations false · transparent · alwaysOnTop · **visible false** |
| externalBin | `cnexus-runtime` + 预构建 `cnexus-runtime-x86_64-pc-windows-msvc.exe` | `npm run build:sidecar` |
| resources | `runtime-bundle/` | `bundle-runtime-for-desktop.ps1` 输出 |
| NSIS hooks | `windows/hooks.nsh` | 卸载/升级前杀进程 |
| Edition | `cnexus-config.json` | personal / enterprise |
| License | `%LOCALAPPDATA%\CNexus\license.cnx` | 企业版 |
| 构建环境 | VS Build Tools + vcvars64 | 普通 PowerShell 无 `link.exe` 会失败 |

**Release 环境变量：** Sidecar 注入 `PYTHONNOUSERSITE=1`、`BRAIN_MEMORY_ROOT`、`BM_MEMORY_DIR`；不依赖开发机 `PYTHONPATH`。

---

## 4️⃣ 编译与构建优化

| 项 | CNexus 配置 |
|----|-------------|
| Release | `panic = "abort"`, `lto`, `strip`, `opt-level = "s"` |
| CRT 静态链接 | 未显式配置 | ⚠️ 目标机需 VC++ 运行库或 WebView2 引导 |
| Sidecar 独立 crate | `cnexus-runtime-sidecar/` | 避免主 crate 误编 sidecar |
| 快速重打包 | `tauri.bundle-only.conf.json` | 跳过 `beforeBuildCommand` |
| Demo / 企业 | `write-cnexus-config.mjs` + `build:personal` / `build:enterprise` | 安装包默认 bundled personal |

**禁止：** UI / Runtime **强壳（UPX 等）** — 审计脚本扫描 `UPX!` 签名。

---

## 5️⃣ 日志与监控

| 项 | 现状 | RC 建议 |
|----|------|---------|
| UI 控制台 | `#![windows_subsystem = "windows"]` on sidecar release | ✅ 无 CMD |
| Runtime 日志 | stdout/stderr → null | ⚠️ 排障靠 `%LOCALAPPDATA%\CNexus\data` 与后续 log 文件 |
| 健康检查 | Rust poll `/v1/health` + 前端 500ms×60 退避 | ✅ |
| WS | `MindRuntimeBridge` state/log 流 | 契约 `WS /ws/state` |
| UI 崩溃 → Runtime | 未心跳 | 手动 `kill-cnexus-runtime.ps1` |

---

## 6️⃣ 打包前最终流水线

```text
[发布门禁 — 先于 build]
  □ npm run prebuild:gate（FAIL = 禁止 build）
  □ 安装态 MANUAL_SIGNOFF.json
  □ npm run prebuild:gate:strict（RC tag）

[代码与依赖]
  ✓ test:demo / test:kernel-boundary
  ...
```

详见 [FINAL_RELEASE_GATE.md](./FINAL_RELEASE_GATE.md)。

---

## ✅ 总结性建议（RC 0.1.0-alpha）

1. **先审计后编译：** `npm run prebuild:audit`，避免 10 分钟编译后才发现缺 `runtime-bundle`。
2. **Runtime 与 UI 加壳策略分离：** 仅签名，不 UPX。
3. **悬浮窗问题 = 启动顺序 + 尺寸 + 资源加载：** 已状态机化，勿回退 `visible:true` / 52×52。
4. **孤儿进程 = 旧安装包 + pythonw 漏杀：** 新包装 + `kill-cnexus-runtime.ps1`。
5. **所有操作可复现：** [CHECKLIST.md](./CHECKLIST.md) + [BUILD_PIPELINE.md](./BUILD_PIPELINE.md) + `LATEST_AUDIT.txt`。

---

## 关键源码索引

| 模块 | 路径 |
|------|------|
| 主入口 | `frontend/src-tauri/src/lib.rs` |
| Sidecar 生命周期 | `frontend/src-tauri/src/runtime_sidecar.rs` |
| 进程清理 | `frontend/src-tauri/src/runtime_cleanup.rs` |
| 启动状态机 | `frontend/src-tauri/src/boot_sequence.rs` |
| Sidecar 入口 | `frontend/src-tauri/cnexus-runtime-sidecar/src/main.rs` |
| 悬浮 Boot | `frontend/components/desktop/DesktopFloatBoot.tsx` |
| Runtime 契约 | `brain-memory-ui/docs/RUNTIME_CONTRACT.md` |
