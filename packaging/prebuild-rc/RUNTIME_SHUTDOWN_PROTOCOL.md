# CNexus Runtime Shutdown Protocol (Draft)

> **定位：** READY 启动链的对称面 — 退出链也必须可验证。  
> **Smoke 覆盖：** `npm run prebuild:smoke` 第 7–8 步（无需单独 `gate-runtime-shutdown-smoke.ps1`）

---

## 问题

关闭 UI 后 Runtime / embedded Python 残留，根因通常是：

1. **信号未达子进程树**（console subsystem、spawn flags 不当）
2. **IO 阻塞**（memory flush、日志、license persist）
3. **UI 未调用 stop**（仅 hide 窗口、强杀 UI 未走 Exit 事件）

---

## 当前实现（代码）

| 层 | 机制 |
|----|------|
| UI 退出 | `RunEvent::Exit` / `ExitRequested` → `stop_runtime_sidecar` |
| Sidecar stop | `child.kill()` + `taskkill /F /T /PID` |
| 兜底 | `force_kill_orphan_runtime()` — IM cnexus-runtime、bundled python、:8000 |
| NSIS | `hooks.nsh` pre-uninstall kill |
| 手动 | `scripts/kill-cnexus-runtime.ps1` |

---

## Smoke 自动化（已实现）

```text
1. spawn sidecar → wait /v1/system/ready + WS
2. taskkill /T /PID <sidecar>   # 模拟 UI stop_runtime_sidecar
3. poll ≤5s: 无 :8000 Listen、无 cnexus-runtime、无 bundled python
4. 若 FAIL → 跑 kill-cnexus-runtime.ps1 → WARN（可恢复）或 FAIL（不可恢复）
5. 记录 shutdown_ms → SMOKE_PASS.json
```

---

## 未来可选（Runtime HTTP）

若需 **优雅 shutdown**（flush 后再 exit），可增加：

```http
POST /v1/system/shutdown
→ 202 { "status": "shutting_down" }
→ poll until connection refused / 503
```

Smoke 可优先 POST shutdown，超时再 taskkill — 当前 sidecar-only 路径已足够 RC。

---

## 人工签核（MANUAL_SIGNOFF）

Strict gate 仍要求人工确认：

- `tray_quit_no_orphan`
- `port_8000_released_after_quit`
- `uninstall_no_orphan`

Smoke 不能替代 **Tauri UI 真实 Exit 路径**；只能证明 Runtime 树可被确定性清理。

---

关联：[RUNTIME_SMOKE_PROTOCOL.md](./RUNTIME_SMOKE_PROTOCOL.md) · [FINAL_RELEASE_GATE.md](./FINAL_RELEASE_GATE.md)
