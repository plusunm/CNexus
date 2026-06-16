# Build Toolchain Readiness

> **命令：** `npm run prebuild:toolchain`  
> **输出：** `TOOLCHAIN_READY.json` + `LATEST_TOOLCHAIN.txt`  
> **Gate：** `prebuild:gate` GATE 0 自动调用

---

## 检查项

| 项 | 要求 |
|----|------|
| `cl.exe` | PATH 可执行 |
| `link.exe` | PATH 可执行（或提示 vcvars64 路径） |
| Windows SDK | `Program Files (x86)\Windows Kits\10` 存在 |
| `rustc` / `cargo` | Rust MSVC 工具链 |
| `node` | >= 20 |
| `npm` | 可用 |
| `npx tauri` | Tauri CLI 可用 |

---

## 典型修复

```powershell
# 打开 VS x64 Native Tools，或：
& "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

npm run prebuild:toolchain
```

`ready: true` 后再：

```powershell
# 方式 A：当前 PowerShell 会话注入（推荐交互开发）
. ..\..\scripts\env-vs-native.ps1 -DotSource
npm run prebuild:toolchain
npm run tauri:build

# 方式 B：无需手动 vcvars — 一键 VS 环境预检（CI 可复现）
npm run env:vs-native              # 验证 vcvars + toolchain
npm run prebuild:vs-preflight      # toolchain + gate + smoke（在 vcvars 子进程中）

# 方式 C：VS x64 Native Tools 终端内直接跑
npm run prebuild:gate
npm run prebuild:smoke
npm run tauri:build
```

---

## 流水线位置

```text
prebuild:toolchain   <- GATE 0
prebuild:gate
prebuild:smoke
tauri:build
prebuild:smoke:ui
```
