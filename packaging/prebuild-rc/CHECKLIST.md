# CNexus RC 打包前检查清单

复制本表到发布 PR / 内部记录，逐项打勾。自动化项由 `npm run prebuild:audit` 填充 `LATEST_AUDIT.txt`。

---

## A. 代码与依赖

- [ ] 仓库根 `VERSION` = `0.1.0-alpha`
- [ ] `package.json` / `Cargo.toml` / `tauri.conf.json` / `pyproject.toml` 版本一致
- [ ] `npm run test:demo` 通过
- [ ] `npm run test:kernel-boundary` 通过
- [ ] `src-tauri/Cargo.lock` 已更新并提交
- [ ] `package-lock.json` 已提交
- [ ] 无临时 debug 页面或未使用 sidecar 入口
- [ ] `brain-memory-ui/docs/RUNTIME_CONTRACT.md` 与 `/v1/*` 路由一致

---

## B. 多进程（UI ↔ Runtime）

- [ ] `npm run build:sidecar` 成功，存在 `cnexus-runtime-x86_64-pc-windows-msvc.exe`
- [ ] `npm run bundle:runtime` 成功，`src-tauri/runtime-bundle/` 含 `python/pythonw.exe` 与 `app/.../api/main.py`
- [ ] 安装后仅通过托盘「退出 CNexus」完全退出（非只关悬浮窗）
- [ ] 退出后无 `cnexus-runtime.exe` / `python(w).exe api.main`
- [ ] `http://127.0.0.1:8000/v1/health` 退出后失败
- [ ] 卸载 Setup 后无残留进程
- [ ] 无 CMD 黑窗（Release sidecar + pythonw）
- [ ] 悬浮窗 360×228，可拖动，非麻将块
- [ ] 启动 ≤30s 内 float 显示且 health ok

---

## C. 配置与环境

- [ ] 在 **VS x64 Native Tools**（或 vcvars64 后）构建
- [ ] `prebuild-check.ps1` 四项 OK（cargo/rustc/link）
- [ ] `tauri.conf.json` float：`visible:false` `360×228` `alwaysOnTop:true`
- [ ] `bundle.externalBin` 含 `cnexus-runtime`
- [ ] `bundle.resources` 含 `runtime-bundle/`
- [ ] `windows/hooks.nsh` 已注册
- [ ] 企业 License 路径 `%LOCALAPPDATA%\CNexus\license.cnx` 可读写

---

## D. 编译与构建

- [ ] `npm run build:tauri` → `out/desktop.html` + static
- [ ] `npm run tauri:build` 或 bundle-only 增量成功
- [ ] 产物：`CNexus_0.1.0-alpha_x64-setup.exe`
- [ ] 安装到干净目录（或 VM）做全链路验收
- [ ] Demo 模式（Web）与 Desktop Runtime 模式分别 smoke test

---

## E. 加壳 / 签名

- [ ] UI exe **未** UPX / 加密壳（审计无 `UPX!`）
- [ ] Runtime exe **未**加壳
- [ ] （可选）Authenticode 签名 CNexus.exe + Setup.exe

---

## F. 日志与监控

- [ ] Release 无 stdout 控制台窗口
- [ ] Runtime 崩溃时 UI 显示 fallback 或重连（非 silent hang）
- [ ] （可选）8h 长跑无句柄泄漏

---

## G. 打包前清理

- [ ] 运行 `scripts/kill-cnexus-runtime.ps1`
- [ ] 确认 :8000 空闲
- [ ] Git 工作区已 commit 或知悉未提交变更

---

**签字 / 日期：** _______________  
**Setup 哈希（可选）：** _______________
