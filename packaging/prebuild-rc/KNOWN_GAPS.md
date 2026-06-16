# RC 0.1.0-alpha 已知缺口与接受边界

诚实列出**尚未实现**或**仅部分实现**的项，避免打包后期望错位。

---

## 接受在 RC 内（document + 脚本缓解）

| 缺口 | 影响 | 缓解 |
|------|------|------|
| **端口固定 8000** | 冲突时 Runtime 起不来 | `kill-cnexus-runtime.ps1`；文档说明 |
| **UI 强杀无 Runtime 自杀** | 任务管理器 End Task 后 python 可能残留 | NSIS 卸载 + kill 脚本；**Gate 人工项**；RC+1 父进程心跳 |
| **Release 无滚动日志文件** | 排障靠 health / 数据目录 | RC+1 写 `%LOCALAPPDATA%\CNexus\logs` |
| **CRT 未静态链接** | 极旧系统可能缺运行库 | WebView2 bootstrapper + VC Redist 说明 |
| **30s boot 超时仍 show float** | Runtime 慢时 UI 先 fallback | 前端 500ms 重试 health |

---

## 计划 RC+1（不阻塞本包）

- 动态端口协商（UI 读 sidecar stdout / 命名 pipe）
- Sidecar 监听 UI 父 PID 退出
- 统一 `/v1/health` service 字段（`cnexus` vs `cnexus-ui-api` 文案）
- Rust 集成测试 + 安装器 E2E
- CI Windows runner 全自动 `prebuild:audit` + `tauri build`

---

## 已关闭（本分支代码已有，需新 Setup + gate PASS 才生效）

- CMD 黑窗（pythonw + windows_subsystem）
- 麻将块窗口（360×228 + boot state lock，超时不再 fake ready）
- Boot state lock（`RUNTIME_READY` + show 前 health 复检）
- 悬浮窗不可拖（dock/bar drag）
- 托盘退出不杀 pythonw（cleanup + Job + port 8000）
- 卸载不杀 Runtime（NSIS hooks）

---

## 勿做

- UI / Runtime **UPX 或加密壳**
- float 窗口 `visible: true` 或默认 52×52
- 删除 `runtime-bundle` 后不 re-bundle 直接 tauri build
