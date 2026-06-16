# 人工验收项（自动化无法替代）

打包机审计 + Smoke 通过后，在**干净 Windows 10/11 x64** 或 VM 上执行。  
签核 JSON：`npm run prebuild:signoff:draft` → 见 [MANUAL_SIGNOFF_GUIDE.md](./MANUAL_SIGNOFF_GUIDE.md)

---

## 0. 签核准备

```powershell
cd brain-memory-ui\frontend
npm run prebuild:gate      # VS x64 Native Tools
npm run prebuild:smoke
npm run prebuild:signoff:draft
```

将候选 `Setup.exe` 路径写入 `MANUAL_SIGNOFF.json` → `release.setup_exe_path`。

---

## 1. 安装与双进程

1. 运行 `CNexus_0.1.0-alpha_x64-setup.exe`
2. 任务管理器应出现：`CNexus.exe` → `cnexus-runtime.exe` → `pythonw.exe`（或 python）
3. **不应**出现 CMD 窗口 → 截图 `03_no_cmd_black_window.png`
4. 浏览器：`GET http://127.0.0.1:8000/v1/health` → `status: ok`
5. 可选：`GET /v1/system/ready` → `status: ready`

**gates:** `installer_install_ok`, `runtime_auto_start_ok`, `no_cmd_black_window_ok`

---

## 2. 悬浮窗

| 检查 | 预期 | 截图 |
|------|------|------|
| 首次显示 | 完整悬浮条 ~360×228，非 52px 麻将块 | `02_float_ui_no_mahjong.png` |
| 拖动 | 标题栏可拖；dock 图标拖动 >4px 可移窗 | |
| 置顶 | 默认 always on top | |
| Alt+Shift+M | 显示/隐藏悬浮条 | optional `alt_shift_m_toggle_ok` |
| DPI 125% / 150% | 布局正常、文字可读 | `04_*` / `05_*` |
| 双显示器 | 拖至副屏不变形 | optional `dual_monitor_float_ok` |

**gates:** `float_ui_ok_no_mahjong` · **optional:** `dpi_125_150_ok`

---

## 3. AppData 路径

确认 `%LOCALAPPDATA%\CNexus\data` 存在且可写（标准用户下创建测试文件）。

**gates:** `appdata_paths_ok` · **optional:** `low_privilege_data_write_ok`

---

## 4. 退出与残留

| 操作 | 预期 | 截图 |
|------|------|------|
| 只关悬浮窗 | UI 仍在托盘，Runtime **仍运行**（设计如此） | |
| 托盘「退出 CNexus」 | 三进程均消失，:8000 不通 | `06_tray_quit_task_manager_empty.png` |
| 验证端口 | `curl http://127.0.0.1:8000/v1/health` 失败 | `07_port_8000_down_after_quit.png` |
| 任务管理器强杀 CNexus.exe | Runtime **可能**残留 → 运行 `kill-cnexus-runtime.ps1` | 日志贴 `artifacts.logs.kill_cnexus_runtime_output` |
| 控制面板卸载 | 无 CNexus / cnexus-runtime / api.main 进程 | `08_uninstall_no_residual.png` |

**gates:** `tray_quit_no_orphan`, `port_8000_released_after_quit`, `uninstall_no_orphan`

---

## 5. 端口占用（可选）

1. 先启动其他占 8000 的服务
2. 再启动 CNexus → 预期 Runtime 启动失败或 health 超时（RC 无动态端口）
3. 释放 8000 后重启 CNexus 恢复正常

---

## 6. 企业 License（可选）

1. 放置 `%LOCALAPPDATA%\CNexus\license.cnx`
2. 重启 CNexus，确认 Runtime 重载

---

## 7. 完成签核

编辑 `packaging/prebuild-rc/MANUAL_SIGNOFF.json`：

- 所有 `gates.*` → `true`
- `gate_notes.*` 填写一句话
- `signoff.signed` → `true`，`signed_by`，`signed_at`

```powershell
npm run prebuild:gate:strict
```

---

## 记录模板（legacy）

| 项 | 结果 | 备注 |
|----|------|------|
| 安装 | ☐ Pass ☐ Fail | |
| 无 CMD | ☐ Pass ☐ Fail | |
| 悬浮窗 | ☐ Pass ☐ Fail | |
| 退出无残留 | ☐ Pass ☐ Fail | |
| 卸载无残留 | ☐ Pass ☐ Fail | |
| DPI 125% | ☐ Pass ☐ Fail | |

（推荐使用 JSON + 截图，见 MANUAL_SIGNOFF_GUIDE.md）
