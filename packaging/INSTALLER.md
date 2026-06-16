# CNexus 统一安装包：两个进程 · RC 0.1.0-alpha

**一个 Setup.exe → 安装后两个进程：**

| 进程 | 可执行文件 | 作用 |
|------|------------|------|
| **1 · UI** | `CNexus.exe` | Tauri 悬浮条 + 大屏 |
| **2 · Runtime** | `cnexus-runtime.exe` | FastAPI 认知内核 · `127.0.0.1:8000` |

UI 启动时自动拉起 Runtime；退出 CNexus 时自动结束 Runtime。

---

## 安装目录（Windows）

```
C:\Program Files\CNexus\
├── CNexus.exe
├── cnexus-runtime.exe          # sidecar 进程
├── resources\
│   └── runtime-bundle\       # Python + wheel + API 薄层
│       ├── python\
│       │   ├── python.exe
│       │   └── Lib\site-packages\
│       └── app\
│           ├── brain-memory-ui\api\
│           ├── config\
│           └── cnexus-config.json
└── ...
```

用户数据：`%LOCALAPPDATA%\CNexus\data`  
企业 License：`%LOCALAPPDATA%\CNexus\license.cnx`

---

## 构建安装包（开发机）

**打包前必跑发布门禁（FAIL = 禁止 build）：**

```powershell
cd brain-memory-ui/frontend
npm run prebuild:gate
```

工程审计（可选）：`npm run prebuild:audit`  
RC 签核：`npm run prebuild:gate:strict` + `MANUAL_SIGNOFF.json`

详见：`packaging/prebuild-rc/FINAL_RELEASE_GATE.md`  
报告：`packaging/prebuild-rc/LATEST_GATE.txt`

```powershell
# 1. 打包 Runtime 资源（Python embed + wheel + API）
cd brain-memory-ui/frontend
npm run bundle:runtime

# 2. 打完整安装包（UI + sidecar + resources）
npm run tauri:build
```

或一步：

```bash
npm run tauri:build
```

产物：`src-tauri/target/release/bundle/nsis/CNexus_0.1.0-alpha_x64-setup.exe`（版本以 `VERSION` 为准）

---

## RC 安装验收链

```
Setup.exe → 安装 → CNexus.exe → cnexus-runtime.exe → GET /v1/health → Memory 面板
```

公开 API 契约：[RUNTIME_CONTRACT.md](../brain-memory-ui/docs/RUNTIME_CONTRACT.md)

---

## 开发模式

`tauri dev` 未 bundle 时：

- 不自动起 Runtime（日志提示）
- 可用 **Demo 模式**，或手动 `python -m api.main`（8000 端口）

设置 `CNEXUS_DEV_REPO` 指向 monorepo 根目录时，sidecar 可回退到本机 Python（debug 构建）。

---

## 个人版 / 企业版（同一安装包）

| 模式 | Runtime 行为 |
|------|----------------|
| 个人版 | `CNEXUS_EDITION=personal`，无 License |
| 企业版 | `CNEXUS_EDITION=enterprise` + `license.cnx` |

见 [EDITIONS.md](../EDITIONS.md)。

---

## 代码入口

| 文件 | 作用 |
|------|------|
| `scripts/bundle-runtime-for-desktop.ps1` | 生成 `runtime-bundle/` |
| `src-tauri/src/bin/cnexus-runtime.rs` | Runtime 进程入口 |
| `src-tauri/src/runtime_sidecar.rs` | UI 拉起/停止 sidecar |
| `tauri.conf.json` | `externalBin` + `resources` |
