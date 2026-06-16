# CNexus 统一安装包 · 个人版 / 企业版

**一个安装包** `CNexus-Setup-x.y.z.exe`，用户下载安装即用。  
个人版与企业版是**同一 EXE 内的两种模式**，不是两个安装包。

---

## 架构：一个安装包 · 两个进程

```
CNexus-Setup.exe
├── CNexus.exe              进程 1 · UI（Tauri）
├── cnexus-runtime.exe      进程 2 · API（127.0.0.1:8000）
└── resources/runtime-bundle/   Python + 认知内核 wheel
```

UI 启动 → 自动 spawn Runtime；退出 → 一并结束。

| 模式 | 如何启用 | 行为 |
|------|----------|------|
| **个人版** | 默认 | Demo 离线；可选连本地 Runtime |
| **企业版** | License 激活 | 必须 Runtime；模型管理；License 校验 |

---

## 构建

```bash
cd brain-memory-ui/frontend
npm run tauri:build
```

内部步骤：`bundle:runtime` → `build:tauri` → `tauri build`

上传：`CNexus_*_setup.exe`（一个文件）

详见 [packaging/INSTALLER.md](./packaging/INSTALLER.md)

---

## 安装后配置 `cnexus-config.json`

默认（个人版）：

```json
{
  "edition": "personal",
  "apiBase": "http://127.0.0.1:8000",
  "wsBase": "ws://127.0.0.1:8000"
}
```

企业版（安装脚本或激活后）：

```json
{
  "edition": "enterprise",
  "apiBase": "http://127.0.0.1:8000",
  "wsBase": "ws://127.0.0.1:8000",
  "apiToken": "与 Runtime CNEXUS_API_TOKEN 一致"
}
```

同目录 `license.cnx` 内容 = `CNEXUS_LICENSE` 字符串。

---

## 企业 License 流程

1. 用户安装同一 EXE（个人版可直接用 Demo）
2. 企业客户向你们索取 License → 提供**机器指纹**（Runtime 未授权启动时会打印）
3. 你们离线执行：

```bash
python scripts/issue_license.py --secret "$CNEXUS_LICENSE_SECRET" --fingerprint "<fp>"
```

4. 用户任选其一：
   - 安装向导填入 License
   - 应用内「已有企业 License？激活企业版」
   - 手动写入 `%ProgramFiles%\CNexus\license.cnx`

5. 重启 Runtime 服务 → 企业版能力解锁（模型管理、完整 cognitive loop）

---

## Runtime 环境（内置侧车）

| 变量 | 个人版（默认） | 企业版 |
|------|----------------|--------|
| `CNEXUS_EDITION` | `personal` | `enterprise` |
| `CNEXUS_LICENSE` | — | 必填 |
| `CNEXUS_API_TOKEN` | — | 建议 |

个人版 Runtime：**可不强制 License**（`license_guard.py` 按 edition 判断）。

---

## 发布流程

```
开发 → npm run tauri:build → CNexus-Setup-x.y.z.exe → 上传
用户 → 下载 → 安装 → 个人直接用 / 企业填 License
更新 → 发新版本安装包（不必 Git、不必 Web 平台）
```

---

## 代码入口

| 模块 | 作用 |
|------|------|
| `cnexus-kernel/edition.ts` | 版本能力；`resolveEdition()` |
| `lib/cnexusConfig.ts` | 读 config + 企业激活 |
| `ConnectionModeGate.tsx` | 首次选 Demo/Runtime + License 激活入口 |
| `api/license_guard.py` | 企业 Runtime License 校验 |
| `scripts/write-cnexus-config.mjs` | 打包时写默认 config |

详见 [packaging/INSTALLER.md](./packaging/INSTALLER.md) 安装目录规范。
