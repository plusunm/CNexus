# CNexus Runtime Smoke Protocol

> **定位：** 静态 Gate 无法验证的「运行时真相探针」。  
> **命令：** `npm run prebuild:smoke` → `packaging/prebuild-rc/LATEST_SMOKE.txt` + `SMOKE_PASS.json`

---

## 为什么必须有 Smoke

| 静态 Gate | Smoke Gate |
|-----------|------------|
| 代码里有没有 BootStateLock | Runtime 能否真的 ready |
| tauri.conf 尺寸对不对 | `/v1/system/ready` 是否 200 |
| sidecar 源码有没有 pythonw | WS 首帧是否到达 |
| **不能**证明无麻将块 | **能**证明启动链闭环 |

> 麻将块 = 时序问题 → 只能运行验证。

---

## Smoke 步骤（自动化）

```text
1. Preflight: sidecar exe + runtime-bundle + PE subsystem
2. kill-cnexus-runtime.ps1（清 8000）
3. Start-Process sidecar -WindowStyle Hidden
4. Poll GET /v1/system/ready (≤45s)
   - require status=ready, ws=alive, token_valid=true
5. GET /v1/health (liveness)
6. ClientWebSocket ws://127.0.0.1:8000/ws/state → first frame contains mind_overview
7. taskkill /T sidecar PID → poll port 8000 + process tree (≤5s)
8. If orphans remain → kill-cnexus-runtime.ps1 recovery probe
9. Write SMOKE_PASS.json { passed, ready_ms, ws_ms, shutdown_ms, total_ms }
```

---

## FAIL 即阻断 build

- sidecar / bundle 缺失
- ready 超时
- WS 握手失败
- runtime 进程早退
- shutdown 后 :8000 仍占用或 sidecar/python 残留
- kill-cnexus-runtime.ps1 无法恢复孤儿进程

---

## 在四层门禁中的位置

```text
prebuild:audit        工程结构
prebuild:gate         工具链 + BootStateLock 静态
prebuild:smoke        ⭐ 运行时探针
prebuild:gate:strict  人工安装态 + smoke 标记
```

---

## CI / 回归

- 同一脚本可在 CI Windows runner 运行（需 bundle + sidecar 预构建）
- `SMOKE_PASS.json` 供 strict 模式校验（24h 内有效）
- 指标 `ready_ms` / `ws_ms` 可建立 baseline 回归

---

## 与 UI BootStateLock 关系

Smoke 验证 **Runtime 侧** READY 语义；UI 侧仍由 `DesktopFloatBoot` + `grant_ui_render` 保证 **show 不早于 STATE≥3**。

两者叠加 = 静态 + 运行时双保险。

---

关联：[RUNTIME_READY_PROTOCOL.md](./RUNTIME_READY_PROTOCOL.md) · [FINAL_RELEASE_GATE.md](./FINAL_RELEASE_GATE.md)
