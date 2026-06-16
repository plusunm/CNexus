# 🚦 CNexus Final Release Gate

> **定位：** 在 `prebuild:audit`（工程结构审计）之上，再叠一层 **「是否允许进入 production build」** 的门禁。  
> **原则：** 自动化项 **FAIL = 禁止 build**；人工项 **未签核 = 禁止打 RC 标签**（`-Strict` 模式）。

---

## 与 `prebuild:audit` 的区别

| 层 | 脚本 | 回答的问题 |
|----|------|------------|
| 工程审计 | `prebuild-audit-full.ps1` | 目录、版本、资源、契约是否齐 |
| **发布门禁** | `prebuild-release-gate.ps1` | **编译环境是否真实可用？启动链是否确定性？安装态是否已签核？** |

---

## 1. 编译环境门禁（Automated · FAIL = 禁止 build）

| 项 | 要求 |
|----|------|
| `cargo --version` | 可执行且在 PATH |
| `rustc --version` | 可执行且在 PATH |
| `where cargo` | 有路径 |
| `where link` | VS `HostX64\x64\link.exe` |
| `where cl` | MSVC 编译器可用 |

⚠️ `prebuild:audit` 对此仅 **WARN**；**Gate 必须全部 PASS**。

---

## 2. 启动确定性门禁（Automated · BootStateLock + `/v1/system/ready`）

| 项 | 要求 |
|----|------|
| `GET /v1/system/ready` | 权威 READY（见 RUNTIME_READY_PROTOCOL.md） |
| BootStateLock | STATE≥3 才 show；Rust poll + JS probe + grant |
| WS handshake | `probeWsStateHandshake` ≤2s |
| Float hidden until ready | 超时 → demo fallback，不 fake ready |
| SHOW_DELAY | ≥100ms |

静态验证 + 协议文档：`RUNTIME_READY_PROTOCOL.md`

---

## 3. 安装态验证（Manual · 必须签核）

在 **干净 Windows VM** 或全新用户配置文件上，用 **上一版或候选 Setup.exe** 完成：

- [ ] Setup.exe 安装成功
- [ ] `%LOCALAPPDATA%\CNexus\data` 可写
- [ ] 安装后双进程 + health OK
- [ ] 悬浮窗非麻将块、可拖动
- [ ] 托盘退出无残留
- [ ] 卸载无残留、`8000` 释放
- [ ] DPI 125% / 150% 抽测

签核文件：[`MANUAL_SIGNOFF.template.json`](./MANUAL_SIGNOFF.template.json) → `MANUAL_SIGNOFF.json`  
生成草稿：`npm run prebuild:signoff:draft` — 见 [`MANUAL_SIGNOFF_GUIDE.md`](./MANUAL_SIGNOFF_GUIDE.md)

---

## 4. 悬浮窗专项（Manual + Automated）

**Automated（Gate 脚本）：** 360×228 · hidden · boot 模块存在  
**Manual：** index/JS 无 404、DPI、多显示器、加壳=OFF

---

## 5. 进程完整性（Manual + 部分 Automated）

**Automated：** cleanup / NSIS hooks / Job Object 源码存在  
**Manual：**

- [ ] UI 正常退出 → Runtime < 2s 消失
- [ ] taskkill CNexus → 运行 `kill-cnexus-runtime.ps1` 可清（RC 已知缺口：无父进程心跳）
- [ ] 无 orphan `pythonw` / `cnexus-runtime`

---

## 命令

```powershell
cd brain-memory-ui\frontend

# 自动化门禁（FAIL 则禁止 build）
npm run prebuild:gate

# 含人工签核检查（RC 打 tag 前）
npm run prebuild:gate:strict
```

报告：`packaging/prebuild-rc/LATEST_GATE.txt`

---

## 允许 build 的判定

```text
prebuild:audit              工程结构齐
prebuild:gate               工具链 + BootStateLock 静态 PASS
prebuild:smoke              ⭐ Runtime 真启动 + /v1/system/ready + WS 首帧
prebuild:gate:strict        smoke≤24h + MANUAL_SIGNOFF.json signed
→ 才允许 npm run tauri:build
```

一键：`npm run prebuild:release`（gate + smoke）

---

## 四层 Release Control Plane

```text
┌─────────────────┐
│ prebuild:audit  │  工程能否编译 / 结构是否正确
└────────┬────────┘
         ▼
┌─────────────────┐
│ prebuild:gate   │  工具链硬 PASS + BootStateLock 静态（不能替代 smoke）
└────────┬────────┘
         ▼
┌─────────────────┐
│ prebuild:smoke  │  ⭐ 运行时真相探针（防麻将块唯一手段）
└────────┬────────┘
         ▼
┌─────────────────┐
│ gate:strict     │  安装态人工 + SMOKE_PASS≤24h
└─────────────────┘
```

报告：

- `LATEST_GATE.txt` / `LATEST_SMOKE.txt` / `SMOKE_PASS.json`

---

关联：[CONSULTATION_SUMMARY.md](./CONSULTATION_SUMMARY.md) · [KNOWN_GAPS.md](./KNOWN_GAPS.md) · [MANUAL_VERIFICATION.md](./MANUAL_VERIFICATION.md)
