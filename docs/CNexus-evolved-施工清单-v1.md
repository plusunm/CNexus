# CNexus-evolved 施工清单 v1

> **母本**：`D:\类脑记忆\CNexus — Observational Cognition Platform`（`0.1.0-alpha`，commit `2f2d074` 附近）  
> **规范源**：`F:\CNexus — Observational Cognition Platform\NEW_CNEXUS\CNEXUS_MIGRATION_RUNBOOK_v3_PURIFIED`  
> **版本对照表**：`D:\类脑记忆\CNexus-D盘版本总表-20260616.md`  
> **生成日期**：2026-06-16  
> **状态**：Layer 1–6 已落地（分支 `evolved/sigma-v0.2`）

---

## 0. 硬约束（Runbook 不可违反）

| 约束 | 含义 | 验收 |
|------|------|------|
| 无新类型 | 不引入 Runbook 未声明的 dataclass / enum | `grep` + schema diff |
| REMAP 纯编译 | `Σ_REMAP` 仅 JSON IR，运行时只读 | 无 Python import 写 mapping |
| 7 层 DAG | memory → trace → cognitive_state → recall → cognition → migration_engine → external_inference | 每层独立 PR + gate |
| 母本优先 | D: `0.1.0-alpha` 为 SSOT；F: 扫描路径可能过期 | 以 D: 实际 tree 为准 |
| 不自动合并多版本 | Runbook 是规范，不是 merge 工具 | 仅 **借** 片段，不 wholesale copy |

---

## 1. 分叉策略

### 推荐工作区

```
方案 A（推荐）：母本 git 分支
  git checkout -b evolved/sigma-v0.2

方案 B：并行目录（仅当需保留 alpha 完全不动时）
  D:\类脑记忆\CNexus-evolved   ← robocopy 母本 + 独立 git init
```

### 借源优先级

1. **D: 母本** — 默认修改目标  
2. **D:\plusunm** — G1 UI 栈、`brain-memory-ui` 438MB、runtime 1.0.0-g1 行为参考  
3. **D:\类脑记忆\CNexus1.0** / `_tmp_cnexus1_compare` — 对照 diff，不直接覆盖  
4. **F: Runbook SANDBOX** — `compiler_output/step_01_mapping_table.json`（44 条 mapping）

---

## 2. 七层 DAG → D: 母本路径映射

> F: Layer1 扫描写的是 `core/memory/observe/record_store.py` — **D: 母本已无此路径**。  
> 等价落点见下表「D: 实际路径」。

### Layer 1 — memory_store（Σ.M）

| Runbook 概念 | D: 实际路径 | 动作 | 备注 |
|--------------|-------------|------|------|
| MemoryBlock / block registry | `memory/block.py` | **KEEP+EXTEND** | 已有 `created_at/updated_at/decay_rate/version/importance` — F: FACTORY_GAP 多数已闭合 |
| Block persistence | `memory/block_store.py` | **MODIFY** | 接入 `sigma_mapping.memory_block_to_sigma_m` |
| Memory manager | `memory/manager.py` | **MODIFY** | STORE 步写 `Σ.M.metadata.iteration_counter` |
| Atomic IO | `memory/atomic_io.py` | **KEEP** | 崩溃安全写 |
| Lifecycle / filter | `memory/lifecycle.py`, `memory/filter.py`, `memory/schema.py` | **KEEP** | |
| ExecutionRecord | `core/kernel/record.py` | **MODIFY** | STORE 投影 → Σ.M |
| ER schema | `core/kernel/schema/execution_record_v1.json` | **KEEP** | v1 冻结，evolved 用 metadata 扩展 |
| **新建** Σ bridge | `core/evolved/sigma_mapping.py` | **NEW** ✅ | Layer1 第一步已落地 |
| SelfModel 写 ownership | `core/self_model/store.py`, `self_model.py` | **MODIFY** | `block_updated_at` writer = STORE_step |

**Layer 1 验收门控**

- [x] `pytest tests/test_sigma_mapping.py` 全绿  
- [x] `MemoryBlock` round-trip → `Σ.M` → `MemoryBlock` 字段不丢  
- [x] `block_store` 持久化含 `metadata.sigma_slot`  
- [x] 无新增 Pydantic model（仅 dict 映射）

---

### Layer 2 — execution_trace（Σ.T）

| Runbook 概念 | D: 实际路径 | 动作 | 备注 |
|--------------|-------------|------|------|
| Append-only trace | `core/runtime/execution_trace.py` | **MODIFY** | 行格式对齐 `trace_id` ↔ ER |
| Trace context | `core/runtime/trace_context.py` | **KEEP+WIRE** | |
| Tap storage | `core/runtime/tap_storage.py` | **KEEP** | |
| Fast ready snapshot | `core/runtime/fast_ready_snapshot.py` | **KEEP** | boot 探针 |
| Kernel router emit | `core/kernel/router.py` | **MODIFY** | 每 intent 写 trace + ER |

**Layer 2 验收**

- [x] `execution_trace.jsonl` 每行含 `trace_id`, `intent_type`, `sigma_trace_slot`  
- [ ] `/v1/system/capability` 仍 ≤90s 达 `full_ready`（不回归 upload 门控）

---

### Layer 3 — cognitive_state（Σ.S + Σ.I）

| Runbook 概念 | D: 实际路径 | 动作 | 备注 |
|--------------|-------------|------|------|
| Unified SelfModel | `core/self_model/` | **MODIFY** | ownership: COGNIZE/DECIDE/STORE |
| Legacy subject model | `core/personality/subject_self_model.py` | **DEPRECATE→REDIRECT** | 读路径合并到 unified |
| Emotion | `core/personality/emotion_engine.py` | **KEEP+WIRE** | COGNIZE_step writer |
| Intent | `core/personality/intent_engine.py` | **KEEP+WIRE** | DECIDE_step writer |
| Belief / DNA | `core/personality/belief/`, `dna_*.py` | **KEEP** | 不拆类型 |
| Reflective | `core/personality/reflective/` | **KEEP** | |

**Layer 3 验收**

- [x] `SelfModelStore` 单文件 SSOT（`unified_self_model.json`）  
- [x] Runbook ownership_table 三 writer 无交叉写冲突（`cognitive_hooks.py`）

---

### Layer 4 — recall（Σ.R）

| Runbook 概念 | D: 实际路径 | 动作 | 备注 |
|--------------|-------------|------|------|
| Recall pipeline | `runtime/recall_pipeline.py` | **MODIFY** | 读 Σ.M rank + `RECALL_PRIORITY_RANK` |
| Hierarchical rank | `memory/block.py` `RECALL_PRIORITY_RANK` | **KEEP** | 已对齐 BlockType |
| Sleep-time compute | `core/memory/sleep_time_compute.py` | **KEEP+WIRE** | |

**借源**：`D:\plusunm` recall 行为（若 latency 更优）— **仅函数级**，不 copy 目录。

---

### Layer 5 — cognition（COGNIZE / DECIDE / STORE 步）

| Runbook 概念 | D: 实际路径 | 动作 | 备注 |
|--------------|-------------|------|------|
| Kernel | `core/kernel/kernel.py` | **MODIFY** | 三步显式 hook |
| Router | `core/kernel/router.py` | **MODIFY** | tier T0/T1/T2 → ER materialize |
| Registry | `core/kernel/registry.py` | **KEEP** | |
| Cognitive warmup | `core/runtime/cognitive_warmup_adapter.py` | **KEEP** | 已修 enterprise 门控 |
| Chat adapter | `core/observation/adapters/chat_adapter.py` | **KEEP** | |

---

### Layer 6 — migration_engine

| Runbook 概念 | D: 实际路径 | 动作 | 备注 |
|--------------|-------------|------|------|
| **新建** migration runner | `core/evolved/migration_runner.py` | **NEW** | 读 SANDBOX JSON，不 embed 逻辑 |
| Mapping IR | `docs/evolved/step_01_mapping_table.ref.json` | **NEW** | 从 F: 复制引用（44 条） |
| Normalization rules | `docs/evolved/LAYER1_NORMALIZATION.ref.md` | **NEW** | 摘要，非执行脚本 |

Runbook 本身 **77 md/json、0 可执行脚本** — 本层在 D: 实现**唯一**可执行入口。

---

### Layer 7 — external_inference

| Runbook 概念 | D: 实际路径 | 动作 | 备注 |
|--------------|-------------|------|------|
| UI / API 边界 | `brain-memory-ui/frontend/` | **KEEP+MODIFY** | 已修 upload gate |
| Runtime sidecar | `brain-memory-ui/frontend/src-tauri/cnexus-runtime-sidecar/` | **KEEP** | `CNEXUS_DEPLOY_LEVEL=internal` |
| API router | `runtime/router.py` | **KEEP** | |
| Capability SSOT | `core/runtime/system_ready.py`（或等价） | **KEEP** | `operational_ready` vs `full_ready` |

**借源**：`D:\plusunm\brain-memory-ui` — Microsoft-style 组件仅当 UX 回归需要时 cherry-pick。

---

## 3. SANDBOX 44 mapping 快速对照

| 分类 | 数量 | D: 母本现状 |
|------|------|-------------|
| exists | 33 | 大部分已在 `memory/block.py` + `core/kernel/record.py` |
| redirect | 8 | `observe/record_store` → `memory/block_store.py` |
| rename | 27 | 文档化即可，代码 alias 在 `normalize_block_label` |
| factory_gap | 4 | **3/4 已在 MemoryBlock**；余 `importance_snapshot` → `state_projection.stability_metrics` |
| merge | 1 | SelfModel `last_reconstruction` ↔ `block_updated_at` |
| partial | 2 | trace timestamp 派生 — `sigma_mapping.derive_timestamps_from_trace` |

完整 IR 路径：  
`F:\...\SANDBOX\compiler_output\step_01_mapping_table.json`

---

## 4. 明确删除 / 不迁移

| 路径 | 原因 |
|------|------|
| F: 扫描中的 `core/memory/observe/*` | D: 已重构为 `memory/*` |
| `_tmp_cnexus1_compare/` 整树 | 仅 diff 参考，不进 evolved |
| `dist/wheels/cnexus_runtime_core-1.0.0` 与 `VERSION=0.1.0-alpha` 混用 | **对齐 wheel 版本** 单独工单 |
| Runbook 内 SANDBOX Python（无） | N/A |

---

## 5. 阶段排期（建议）

| 周 | 层 | 交付物 |
|----|-----|--------|
| W1 | L1 | `sigma_mapping` + block_store 集成 + tests ✅ 进行中 |
| W2 | L2 | trace 行格式 + router 双写 |
| W3 | L3 | SelfModel ownership 拆分 |
| W4 | L4–L5 | recall rank + kernel 三步 hook |
| W5 | L6 | migration_runner + mapping IR 引用 |
| W6 | L7 | E2E：upload + chat + installer 回归 |

---

## 6. 第一周执行序列（已启动）

```text
[x] 1. 编写本施工清单
[x] 2. 新增 core/evolved/sigma_mapping.py
[x] 3. 新增 tests/test_sigma_mapping.py
[x] 4. memory/block_store.py 读写 metadata.sigma_slot
[x] 5. core/kernel/record.py STORE 投影调用 sigma_mapping
[x] 6. 从 F: 复制 step_01_mapping_table.json → docs/evolved/step_01_mapping_table.ref.json
[x] 7. git branch evolved/sigma-v0.2
[x] 8. core/evolved/store_step.py + trace_emit.py + cognitive_hooks.py + migration_runner.py
[x] 9. kernel._persist_record 双写 Σ.T trace + cognitive ownership
[x] 10. recall_pipeline._apply_sigma_ranking (Layer 4)
[x] 11. tests/test_evolved_integration.py (7 cases)
```

---

## 7. 风险登记

| 风险 | 缓解 |
|------|------|
| F: 路径与 D: 不一致 | 以本清单「D: 实际路径」为准，每 PR 更新表 |
| wheel 1.0.0 vs alpha 标签 | Layer7 前统一 `pyproject`/CI wheel 版本 |
| plusunm 借代码许可证/分叉 | 仅借已存在于母本的模块模式 |
| upload `full_ready` 回归 | 每层合并后跑 `test_system_capability.py` + 手动 upload |

---

*维护：每完成一层，在本文件对应节打勾并追加 commit hash。*
