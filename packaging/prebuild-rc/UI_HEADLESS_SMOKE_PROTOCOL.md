# CNexus UI Headless Smoke Protocol (Phase 2)

> **定位：** 覆盖 Tauri UI 生命周期 — 窗口 / BootStateLock / 托盘退出链 — 静态 Gate 与 Runtime-only Smoke 无法验证的部分。  
> **命令：** `npm run prebuild:smoke:ui` → `LATEST_UI_SMOKE.txt` + `UI_SMOKE_PASS.json`

---

## 前置条件

**必须先有 `CNexus.exe`**（release 构建或已安装副本）：

```powershell
# VS x64 Native Tools
cd brain-memory-ui\frontend
npm run tauri:build
# 或指定已安装路径
powershell -File ../../scripts/prebuild-ui-smoke-gate.ps1 -ExePath "$env:LOCALAPPDATA\Programs\CNexus\CNexus.exe"
```

---

## 机制

| 组件 | 行为 |
|------|------|
| `CNEXUS_UI_SMOKE=1` | UI 进程写入 `%LOCALAPPDATA%\CNexus\data\ui-smoke-report.json` |
| BootStateLock | 每次状态变迁更新 report |
| `FloatWindowShown` | report + **1.2s 后 graceful exit**（`CNEXUS_UI_SMOKE_AUTO_EXIT=0` 可禁用） |
| `tauri-plugin-single-instance` | 二次启动被拒绝，UI smoke 双开验证 |
| 脚本 | report + READY + **WS 首帧** + Win32 窗口 + 分阶段 ms 指标 |

---

## 步骤

```text
0. Single instance: 连续 spawn x2 -> 仅一个 CNexus 存活
1. Preflight: CNexus.exe + sidecar/bundle
2. kill-cnexus-runtime + CNexus
3. CNEXUS_UI_SMOKE=1 -> spawn CNexus (minimized)
4. Poll <=90s (记录 ms):
   - ui_boot_ms, runtime_ready_ms, ws_connected_ms, float_window_ms
5. Wait graceful exit (<=20s)
6. Verify :8000 down + no orphan processes
7. UI_SMOKE_PASS.json
```

---

## 在四层门禁中的位置

```text
prebuild:smoke       Runtime-only 探针
prebuild:smoke:ui    ⭐ UI + Runtime 全链路（Phase 2）
MANUAL_SIGNOFF       安装态 / DPI / 卸载（仍需要）
prebuild:gate:strict RC 放行
```

---

## FAIL 场景

- `CNexus.exe` 不存在
- boot_state 不到 4（麻将块 / grantUiRender 未走通）
- float 窗口不可见或过小
- WS `/ws/state` 握手失败
- 双开 CNexus 导致双 Runtime / 端口冲突

---

关联：[RUNTIME_SMOKE_PROTOCOL.md](./RUNTIME_SMOKE_PROTOCOL.md) · [MANUAL_SIGNOFF_GUIDE.md](./MANUAL_SIGNOFF_GUIDE.md)
