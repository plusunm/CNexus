# CNexus RC 构建流水线

> 必须在 **Visual Studio x64 Native Tools Command Prompt**（或先运行 `vcvars64.bat`）中执行，否则 `link.exe` 不可用。

---

## 0. 进入工程

```powershell
cd "D:\类脑记忆\CNexus — Observational Cognition Platform\brain-memory-ui\frontend"
```

---

## 1. 打包前审计（~30s）

```powershell
npm run prebuild:audit
```

阅读：`packaging/prebuild-rc/LATEST_AUDIT.txt`  
若有 FAIL，修复后再继续。

---

## 2. 清理孤儿进程

```powershell
powershell -ExecutionPolicy Bypass -File ..\..\scripts\kill-cnexus-runtime.ps1
```

---

## 3. 完整构建（~10–20 min，含 bundle + NSIS）

```powershell
npm run tauri:build
```

内部顺序：

1. `prebuild-check.ps1`
2. `tauri:icons`
3. `bundle:runtime` → `src-tauri/runtime-bundle/`
4. `build:tauri` → `out/`
5. `build:sidecar` → `cnexus-runtime-x86_64-pc-windows-msvc.exe`
6. `tauri build` → NSIS

---

## 4. 增量重打包（已存在 out + runtime-bundle + sidecar）

```powershell
npm run build:sidecar
npx tauri build --bundles nsis --config src-tauri/tauri.bundle-only.conf.json
```

---

## 5. 产物

```
src-tauri\target\release\bundle\nsis\CNexus_0.1.0-alpha_x64-setup.exe
```

---

## 6. 安装后 smoke test

```powershell
# 安装后
curl http://127.0.0.1:8000/v1/health
# 托盘 → 退出 CNexus
powershell -File ..\..\scripts\kill-cnexus-runtime.ps1
# 再次 curl 应失败
```

详见 [MANUAL_VERIFICATION.md](./MANUAL_VERIFICATION.md)。
