# MANUAL_SIGNOFF 半自动签核指南

> **目标：** 人工安装态验收 **可记录、可 diff、可挂 Smoke/Gate 指标**，供 `prebuild:gate:strict` 使用。

---

## 快速流程

```powershell
cd brain-memory-ui\frontend

# 1. 自动化门禁（VS x64 Native Tools）
npm run prebuild:gate
npm run prebuild:smoke

# 2. 生成签核草稿（挂接 SMOKE_PASS + LATEST_GATE）
npm run prebuild:signoff:draft

# 3. 在干净 VM / 用户配置安装 Setup.exe，按 MANUAL_VERIFICATION.md 操作

# 4. 截图放入 signoff-artifacts/<version>/<timestamp>/

# 5. 编辑 packaging/prebuild-rc/MANUAL_SIGNOFF.json
#    - gates.* → true
#    - gate_notes.* → 简短说明
#    - signoff.signed → true, signed_by, signed_at

# 6. 严格门禁 + RC 摘要

npm run prebuild:rc-report      # SIGNOFF_SUMMARY.md（给人看）
npm run prebuild:gate:strict
```

---

## JSON 结构（schema 1.1）

| 区块 | 用途 |
|------|------|
| `automated_attached` | 由 `prepare-manual-signoff.ps1` 填入 Smoke/Gate 快照 |
| `machine_context` | 签核机器 OS / DPI / Admin / 路径 |
| `artifacts` | 截图、日志、路径证据（相对 repo 或绝对路径均可） |
| `gates` | **Strict 必填** — 全部为 `true` 且 `signoff.signed=true` |
| `optional_gates` | DPI、低权限写盘、注册表等 — Strict 下缺失会 **WARN** |
| `gate_notes` | 每项人工观察一句话（便于 RC 追溯） |

---

## Strict 必填 gates（7+1）

| Key | 验证内容 |
|-----|----------|
| `installer_install_ok` | Setup 成功 |
| `appdata_paths_ok` | `%LOCALAPPDATA%\CNexus\data` 存在可写 |
| `runtime_auto_start_ok` | 安装后 health / ready |
| `float_ui_ok_no_mahjong` | ~360×228 完整悬浮条 |
| `no_cmd_black_window_ok` | 无 CMD 黑窗 |
| `tray_quit_no_orphan` | 托盘退出后进程树清空 |
| `uninstall_no_orphan` | 卸载无残留 |
| `port_8000_released_after_quit` | 退出后 :8000 不通 |

---

## 推荐截图清单

| 文件 | 内容 |
|------|------|
| `01_installer_complete.png` | 安装完成 / 开始菜单快捷方式 |
| `02_float_ui_no_mahjong.png` | 悬浮窗完整 UI |
| `03_no_cmd_black_window.png` | 启动后桌面无黑窗 |
| `06_tray_quit_task_manager_empty.png` | 托盘退出后任务管理器 |
| `07_port_8000_down_after_quit.png` | `curl :8000` 失败或 kill 脚本输出 |
| `08_uninstall_no_residual.png` | 卸载后无 CNexus 进程 |

DPI 125% / 150%：`04_*` / `05_*` → 对应 `optional_gates.dpi_125_150_ok`

---

## 与 Smoke 的关系

| 层 | 覆盖 |
|----|------|
| `prebuild:smoke` | Runtime READY + WS + shutdown_ms（无 UI） |
| `MANUAL_SIGNOFF` | Tauri UI、托盘、安装路径、DPI、卸载 |

Smoke **不能**替代 `tray_quit_no_orphan` — 必须人工或 Phase 2 UI headless。

---

## 重新生成草稿

```powershell
npm run prebuild:signoff:draft -- -Force
```

`-Force` 会覆盖 `MANUAL_SIGNOFF.json`；已填写的 gates 会丢失，请先备份。

---

关联：[MANUAL_VERIFICATION.md](./MANUAL_VERIFICATION.md) · [FINAL_RELEASE_GATE.md](./FINAL_RELEASE_GATE.md)
