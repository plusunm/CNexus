# CNexus RC 打包前归集目录



> **架构主线：** `CNexus.exe` (Tauri UI) + `cnexus-runtime.exe` (Sidecar) + 内嵌 Python (`127.0.0.1:8000`)  

> **版本：** 以仓库根 `VERSION` 为准（当前 `0.1.0-alpha`）  

> **原则：** 本目录只新增文档与脚本引用，**不删除**仓库内任何既有文件。



---



## 两层门禁（先看这个）



| 层 | 命令 | 能否 build |

|----|------|------------|

| 工程审计 | `npm run prebuild:audit` | 结构齐，但工具链可能仅 WARN |

| **发布门禁** | **`npm run prebuild:gate`** | **FAIL = 禁止 build** |

| **运行时探针** | **`npm run prebuild:smoke`** | **防麻将块/race（不可省略）** |
| **UI 探针 (P2)** | **`npm run prebuild:smoke:ui`** | **需 CNexus.exe（build 后）** |

| RC 打 tag | `npm run prebuild:gate:strict` | smoke≤24h + `MANUAL_SIGNOFF.json` |
| 签核草稿 | `npm run prebuild:signoff:draft` | 挂接 Smoke/Gate + 截图目录 |
| RC 摘要 | `npm run prebuild:rc-report` | 生成 `SIGNOFF_SUMMARY.md`（给人看） |



👉 必读：[FINAL_RELEASE_GATE.md](./FINAL_RELEASE_GATE.md) · [RUNTIME_SMOKE_PROTOCOL.md](./RUNTIME_SMOKE_PROTOCOL.md) · [MANUAL_SIGNOFF_GUIDE.md](./MANUAL_SIGNOFF_GUIDE.md)



---



## 文档索引



| 文档 | 用途 |

|------|------|

| **[FINAL_RELEASE_GATE.md](./FINAL_RELEASE_GATE.md)** | **发布门禁（自动化 + 人工签核）** |
| **[RUNTIME_READY_PROTOCOL.md](./RUNTIME_READY_PROTOCOL.md)** | **Runtime READY 语义 + BootStateLock** |

| **[RUNTIME_SMOKE_PROTOCOL.md](./RUNTIME_SMOKE_PROTOCOL.md)** | **运行时 Smoke 探针** |

| [CONSULTATION_SUMMARY.md](./CONSULTATION_SUMMARY.md) | 六段式会诊总结 |

| [CHECKLIST.md](./CHECKLIST.md) | 可勾选流水线清单 |

| [BUILD_PIPELINE.md](./BUILD_PIPELINE.md) | VS Native Tools 构建步骤 |

| [MANUAL_VERIFICATION.md](./MANUAL_VERIFICATION.md) | 安装态人工验收 |

| [KNOWN_GAPS.md](./KNOWN_GAPS.md) | 已知缺口与 RC 边界 |

| [MANUAL_SIGNOFF.template.json](./MANUAL_SIGNOFF.template.json) | 人工门禁签核模板 |
| **[MANUAL_SIGNOFF_GUIDE.md](./MANUAL_SIGNOFF_GUIDE.md)** | **半自动签核流程 + 截图清单** |
| [RUNTIME_SHUTDOWN_PROTOCOL.md](./RUNTIME_SHUTDOWN_PROTOCOL.md) | 退出链 Smoke 对称协议 |



关联既有文档（仍在 `packaging/` 根目录）：



- [../INSTALLER.md](../INSTALLER.md)

- [../PREBUILD_AUDIT_FLOAT.md](../PREBUILD_AUDIT_FLOAT.md)

- [../BOOT_STATE_MACHINE.md](../BOOT_STATE_MACHINE.md)



---



## 命令



```powershell

cd brain-memory-ui\frontend



# 1. 发布门禁（build 前必过）

npm run prebuild:gate



# 2. 运行时 Smoke（真启动 Runtime）

npm run prebuild:smoke



# 3. 工程审计（可选）

npm run prebuild:audit



# 4. RC 签核（打 tag / 对外发布前）

npm run prebuild:gate:strict

```



报告：



- `LATEST_GATE.txt` — 门禁结果
- `SIGNOFF_SUMMARY.md` — RC 签核人类可读摘要（`npm run prebuild:rc-report`）

- `LATEST_SMOKE.txt` / `SMOKE_PASS.json` — Smoke 探针

- `LATEST_AUDIT.txt` — 工程审计结果



---



## 推荐顺序（不要跳过 gate / smoke）



```text

1. prebuild:gate           <- VS x64 Native Tools, FAIL 则停止

2. prebuild:smoke          <- Runtime READY + WS + shutdown

3. tauri:build             <- 仅 gate + smoke PASS 后

4. prebuild:smoke:ui       <- UI BootStateLock + float + exit (需 CNexus.exe)

5. 安装 Setup -> signoff:draft -> 人工签核

6. prebuild:rc-report -> prebuild:gate:strict

```

快捷：`npm run prebuild:release` = gate + smoke



---



## 产物



```

brain-memory-ui/frontend/src-tauri/target/release/bundle/nsis/

  CNexus_0.1.0-alpha_x64-setup.exe

```


