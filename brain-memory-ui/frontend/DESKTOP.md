# CNexus Desktop (Tauri 2)

桌面版将现有 **FloatingMindBar** 封装为系统级悬浮窗，行为接近搜狗输入法悬浮条。

## 前置条件

- [Node.js](https://nodejs.org/) 20+
- [Rust](https://rustup.rs/) 1.77+（含 `cargo`）
- Windows：WebView2（Win10/11 通常已自带）
- macOS：`xcode-select --install`

## 开发

**日常改 UI：不要打包、不要卸载安装版。**

| 方式 | 命令 / 桌面 | 速度 | 适用 |
|------|-------------|------|------|
| 浏览器 | 桌面 `CNexus-浏览器调试.bat` 或 `npm run dev:browser` | 最快 | 纯前端布局/样式 |
| Tauri 悬浮窗 | 桌面 `CNexus-开发调试.bat` 或 `npm run dev:desktop` | 快 | 窗口/托盘/快捷键 |
| 发版安装包 | 桌面 `CNexus-生成安装包.bat` | 8~15 min | **仅满意后再跑** |

```bash
cd brain-memory-ui/frontend
npm install
npm run dev:desktop    # API + Tauri 热更新
# 或
npm run dev:browser    # API + 浏览器 http://localhost:3000/desktop
```

- 开发模式自动结束已安装版的 Runtime 进程（**无需卸载**），释放 `:8000`
- 改 `components/`、`app/` 等保存后数秒内刷新
- `tauri:dev` 不再每次重新生成 icons（仅首次缺图标时生成）

## 打包（统一安装包）

**确认 UI 无误后再执行：**

```bash
npm run build:installer
# 或双击桌面 CNexus-生成安装包.bat
```

- 默认 **个人版**：Demo 离线
- **企业版**：同一 EXE，安装时或应用内填入 License 激活

详见仓库根目录 [EDITIONS.md](../../EDITIONS.md)。

## 桌面能力

| 能力 | 实现 |
|------|------|
| 无边框透明圆角 | `decorations: false`, `transparent: true` |
| Dock 52px → Bar/Expanded 自动扩窗 | `sync_float_window` + `FloatingMindBar` stage |
| 拖动 | 标题栏 `startDragging()` |
| 位置记忆 | `localStorage` → `cnexus-tauri-window-position` |
| 全局置顶 | `alwaysOnTop` + 面板内 Pin 切换 |
| 全局快捷键 | **Alt+Shift+M**（Rust global-shortcut） |
| 系统托盘 | 显示/隐藏、大屏、开机自启、退出 |
| Runtime | 沿用 `CNEXUS_API_BASE` / `cnexus-config.json` |

## 双窗口

| 窗口 | Label | 用途 |
|------|-------|------|
| 悬浮条 | `float` | 日常 Chat / Memory / Upload |
| 大屏 | `dashboard` | 概览 / 认知全屏 UI |

## 环境变量（Runtime）

```bash
# Windows 用户环境变量或安装目录旁 cnexus-config.json
CNEXUS_API_BASE=http://localhost:8000
CNEXUS_WS_BASE=ws://localhost:8000
```

## 与 Web 版差异

- Web：悬浮条在浏览器 viewport 内 `position: fixed`
- Desktop：**整个 Tauri 窗口**就是悬浮条，可浮在其它应用之上

## 文件结构

```
frontend/
├── app/desktop/          # Tauri 悬浮窗入口
├── lib/tauriDesktop.ts   # JS ↔ Rust bridge
├── hooks/useTauriDesktopSync.ts
├── src-tauri/            # Rust 壳（托盘/快捷键/窗口）
└── DESKTOP.md
```
