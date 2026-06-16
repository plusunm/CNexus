# CNexus 打包前审计 — 悬浮窗 + Runtime 稳定性

> RC 0.1.0-alpha · 打包前必跑  
> 自动化脚本：`scripts/prebuild-audit-float.ps1`

## 7.1 窗口创建强约束

- [ ] `tauri.conf.json` float：`width=360` `height=228`（禁止默认 52×52 启动）
- [ ] `decorations: false` · `transparent: true` · `alwaysOnTop: true`
- [ ] `visible: false` — 禁止创建即显示
- [ ] Rust `boot_sequence::prepare_float_window` 启动时 hide + 设尺寸
- [ ] 前端 `DesktopFloatBoot` 就绪后 invoke `show_float_window`（延迟 ≥120ms）

## 7.2 麻将块 / 残缺 UI

- [ ] `frontendDist` → `../out` 且 `out/desktop.html` 存在
- [ ] `out/_next/static/` 无缺失 chunk（build 后 audit 脚本检查）
- [ ] UI EXE **禁止** UPX/加密壳（仅 Authenticode 签名）
- [ ] Runtime sidecar **禁止**加壳
- [ ] DPI 125% / 150% 手工抽测（LogicalSize 已用）

## 7.3 启动顺序（状态机）

```text
1. UI process start → float hidden
2. Runtime sidecar spawn
3. Rust poll GET /v1/health → emit cnexus:runtime-ready
4. MindConnectionProvider hydrate + preference=runtime
5. FloatingBarStore hydrate + sync_float_window
6. show_float_window (delay 120ms)
7. MindRuntimeBridge probe + WS
```

禁止：Runtime 未 ready 就 show；52px 窗口渲染 bar UI。

## 7.4 健康检查指标

- [ ] UI 创建 window ≤ 300ms
- [ ] Runtime ready ≤ 30s（通常 ≤ 5s）
- [ ] 首次 `probeRuntime` 带 500ms 退避重试（≤ 60 次）
- [ ] show 前 sleep 120ms

## 7.5 加壳风险

| 组件 | 允许 | 禁止 |
|------|------|------|
| CNexus.exe | 签名 | UPX / Themida / VMProtect |
| cnexus-runtime.exe | 原生 | 任何壳 |
| python(w).exe | 嵌入原版 | 二次加壳 |

## 7.6 进程清理

- [ ] 托盘「退出 CNexus」→ 无 cnexus-runtime / api.main python
- [ ] 卸载 NSIS hooks 杀三进程
- [ ] sidecar Job Object + taskkill /T

## 7.7 CMD 黑窗

- [ ] sidecar `#![windows_subsystem = "windows"]`
- [ ] Python 用 `pythonw.exe`（fallback `python.exe` + CREATE_NO_WINDOW）
- [ ] stdout/stderr → null（不 inherit 控制台）

## 7.8 悬浮拖动

- [ ] bar / expanded：`FloatingHeaderBar` → `startDragging`
- [ ] dock：pointer 移动阈值 → drag；纯点击 → 展开

## 打包命令（VS Native Tools）

```powershell
cd brain-memory-ui\frontend
powershell -File ..\..\scripts\prebuild-audit-float.ps1
npm run prebuild:check
npm run build:sidecar
npx tauri build --bundles nsis --config src-tauri/tauri.bundle-only.conf.json
```

## 安装后验收

1. 无双 CMD 窗口
2. 悬浮条 360×228，可拖动标题栏 / dock 图标
3. `GET http://127.0.0.1:8000/v1/health` → ok
4. 退出后 :8000 不可达
5. 卸载后 tasklist 无残留
