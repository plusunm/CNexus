# Layer 1 EXTRACT — D 盘 CNexus 正式提取结果

- **阶段**: SCAN → EXTRACT（结构提取，不含 REMAP 设计）
- **日期**: 2026-06-19
- **目标根**: `D:\类脑记忆\CNexus — Observational Cognition Platform`
- **Runbook 基线**: `F:\CNexus — Observational Cognition Platform\NEW_CNEXUS\CNEXUS_MIGRATION_RUNBOOK_v3_PURIFIED`
- **约束**: EXTRACT FILTER — 只提取结构，不提取行为
- **关联**: `LAYER1_RECONCILE`（对账）、`LAYER1_EXTRACT_DIFF`（drift）、`SANDBOX_BOOT_DRY_RUN`、`X2_X3_CALLSITE_AUDIT`

---

## 0. 路径勘误（相对 F Runbook SCAN）

| F Runbook 旧路径 | D 实际路径 |
|------------------|-----------|
| `core/memory/schema/execution_record_v1.json` | `core/kernel/schema/execution_record_v1.json` |
| `core/memory/observe/record_store.py` | `core/kernel/observe/record_store.py` |
| `core/memory/observe/record_view.py` | `core/kernel/observe/record_view.py` |
| `core/memory/replay/engine_v1.py` | `core/kernel/replay/engine_v1.py` |

---

## 1. Σ.M Block Schema

### 1.1 源：`execution_record_v1.json` + `ExecutionRecord` dataclass

**Schema 路径**: `core/kernel/schema/execution_record_v1.json`  
**类路径**: `core/kernel/record.py`

#### Block 顶层结构

```
ExecutionRecord / execution-record-v1:
  version:           const "execution-record-v1"
  trace_id:          string (minLength 1)
  intent_type:       string
  result:            any
  identity:          string | null
  graph_invariant:   string | null
  graph:             object | null
  nodes:             array[object]
  edges:             array[object]
  state_projection:  object
  causal_projection: object
  explain_projection: object
  replay_signature:  string | null
  audit:             object
  audit_log:         object
  events:            array[object]
  derivation:        object
  elapsed_ms:        number
  equivalence:       object | null          # D/F 有，Runbook IR 未映射
```

#### state_projection 内部（`_build_state_projection`）

```
state_projection:
  ok, status, skipped, reason:  from result dict
  stability_metrics:            object  → importance_snapshot 子集 (partial)
  total, by_layer:               governance 统计
  intent, result_type:           fallback 非 dict result
```

#### causal_projection 内部

```
causal_projection:
  edge_count, node_count: int
  edges:                  array (max 32)
  scheduler:              string | null
  execution_tier:         string (lazy expand only)
```

### 1.2 D 独有 side-channel（schema 外，Runbook 合规）

| 方法 | 输出 slot | 模块 |
|------|-----------|------|
| `ExecutionRecord.build_store_projection()` | Σ.M | `core/evolved/store_step.py` |
| `ExecutionRecord.build_sigma_trace()` | Σ.T | `core/evolved/sigma_mapping.py` |

### 1.3 Kernel 持久化 store（非 v1 schema 文件）

**类**: `KernelRecordStore` — `core/kernel/observe/record_store.py`

| API | 持久化 |
|-----|--------|
| `append(row: dict)` | `{base}/observability/kernel_records.jsonl` |
| `get(trace_id)` | 内存 index |
| `list_trace_ids(limit)` | trace_id 列表 |

**替代 Runbook**: `observe_record()` → `append()`

### 1.4 MemoryBlock Σ.M（母本 memory 层）

**类**: `MemoryBlock` + `MemoryBlockStore` — `memory/block_store.py`  
**D evolved**: `sigma_mapping.memory_block_to_sigma_m()` / `apply_sigma_to_block()`

| MemoryBlock 字段 | Runbook canonical | factory_gap |
|-----------------|-------------------|-------------|
| block_id | block_id | exists |
| label | block_label | exists |
| content | block_payload | exists |
| importance | block_importance_snapshot | partial |
| decay_rate | block_decay_rate | **D 已实现** |
| created_at / updated_at | block_created_at / block_updated_at | **D 已实现** |
| version | block_version_seq | **D 已实现** |
| metadata.sigma_slot | — | D extension `"Σ.M"` |

---

## 2. Σ.T Interface Shape

### 2.1 trace 行（append_execution_trace）

**模块**: `core/runtime/execution_trace.py`

```
Σ.T.Entry (jsonl row):
  ts:         float
  mono_ms:    int
  type:       string
  ...rest:    any (payload)

文件: {base_dir}/execution_trace.jsonl
写入: 线程锁 + append-only
```

### 2.2 trace_stats 输出

| 旧字段 | Runbook canonical | D/F |
|--------|-------------------|-----|
| path | trace_store_path | ✅ |
| exists | trace_store_exists | ✅ |
| readable | trace_store_readable | ✅ |
| total_lines | trace_total_entries | ✅ |
| l3_tick_count | trace_loop_iterations | ✅ |
| **interaction_step_count** | *(IR 未映射)* | **D only** |
| last_tick_ms | trace_last_loop_mono_ms | ✅ |
| last_event_type | trace_last_event_type | ✅ |
| flow_active | trace_flow_alive | ✅ |
| no_flow | trace_flow_stopped | ✅ |

### 2.3 trace_context

**模块**: `core/runtime/trace_context.py`

```
trace_id: "trace-" + uuid.hex[:12]
API: start_trace / get_trace_id / trace_scope / resolve_trace_id
传播: ContextVar
```

Runbook NORMALIZE 目标 `t-` + hex[:16] — **D 未实施**。

### 2.4 D evolved kernel_execution 行

**模块**: `core/evolved/trace_emit.py`

```
type: kernel_execution
phase: kernel_record
trace_id, intent_type, sigma_trace_slot=Σ.T
elapsed_ms, identity, graph_invariant, importance_snapshot
```

---

## 3. SelfModel 持久化字段

### 3.1 数据结构（`core/self_model/self_model.py` — D/F 相同）

```
SelfModel:
  identity_summary:          string (max 600)
  autobiographical_story:    string (max 1200)
  core_beliefs:              dict[str, float]
  relational_models:         dict[str, {trust, tone}]
  self_expectations:         dict[str, float]
  future_projection:         dict[str, any]
  stable_behavioral_bias:    dict[str, float]
  coherence_score:           float
  last_reconstruction:       ISO datetime string
  total_experiences:         int
```

**文件**: `{base}/unified_self_model.json`（回退 `subject_self_model.json`）  
**Store**: `core/self_model/store.py`

### 3.2 Runbook 域拆分表

| 字段 | 目标域 | Writer 步 |
|------|--------|----------|
| identity_summary, autobiographical_story, core_beliefs | Σ.I | DECIDE |
| self_expectations, stable_behavioral_bias | Σ.I | DECIDE |
| relational_models, future_projection, coherence_score | Σ.S | COGNIZE |
| last_reconstruction, total_experiences | Σ.M metadata | STORE |

### 3.3 D evolved writer 实现

| 函数 | 文件 | 持久化现实 |
|------|------|-----------|
| `apply_cognize_step` | cognitive_hooks.py | 仍 `save()` 全文件 |
| `apply_decide_step` | cognitive_hooks.py | 同上 |
| `apply_store_selfmodel_step` | cognitive_hooks.py | 同上 |
| `store_step_touch` | store.py | 同上 |

**标记**: `SPLIT_PERSISTENCE_REQUIRED` — 见 `X2_X3_CALLSITE_AUDIT.md`

---

## 4. Registry Keys

**文件**: `core/kernel/registry.py` — D/F **0 差异**

| intent_type | handler_path |
|-------------|--------------|
| chat | runtime.process_interaction |
| recall | runtime.recall |
| capture | runtime.capture |
| control / cdg_apply | runtime.run_governance_cycle |
| ir_exec | ir_kernel.compile_and_execute |
| system | ir_kernel.compile_graph |
| memory_maintenance | runtime.run_memory_maintenance |
| capture_cognition | runtime.process_capture_cognition |
| reflect_review | runtime.trait_based_reflection |
| reflect_due_reviews | runtime.reflection_pipeline.run_due_reviews |
| governance_validate | runtime.run_validation_suite |
| observe | kernel.observe |

**结论**: CONFIG SPACE，不在 Σ 中。

---

## 5. Observe 读模型

### 5.1 合规 SSOT

**`ExecutionRecordView`** — `core/kernel/observe/record_view.py`

```
read(trace_id, kernel) → ExecutionRecordView
字段: trace_id, identity, graph, nodes, edges,
      state/causal/explain_projection, replay_signature,
      audit_log, intent_type, elapsed_ms
```

### 5.2 Runbook violation 路由

**`core/kernel/router.py::_route_observe`**

| kind | 实现 |
|------|------|
| memory_stats | `runtime.memory_stats()` |
| governance_state | `runtime.get_current_state()` |
| cdg_trajectory | `runtime.cdg.trajectory_report()` |
| active_reflections | `reflection_pipeline.get_active_reflections()` |

详见 `X2_X3_CALLSITE_AUDIT.md` §X3。

---

## 6. Replay Engine（CP-3）

**文件**: `core/kernel/replay/engine_v1.py`

```
ExecutionGraphReplayEngineV1.replay(graph):
  - scheduler.run(replay_graph) — 图重放，非 jsonl 直读
  - identity_index 校验
  - record_execution_tap(...)
```

**Runbook X1 修正**: 旧描述「从 execution_trace.jsonl 恢复 state」**部分过时**；现为主动图重放。trace 污染风险仍在（jsonl 可被其他消费者读）。

---

## 7. Σ REMAP 44 映射 — D 适用性

**IR**: `docs/evolved/step_01_mapping_table.ref.json`（与 Runbook SANDBOX **hash 一致**）

| 分类 | 数量 | D 状态 |
|------|------|--------|
| exists | 33 | ✅ |
| rename | 27 | ✅ |
| redirect | 8 | ✅ |
| factory_gap | 4 | ✅ D evolved 运行时闭合 |
| merge | 1 | ✅ |
| partial | 2 | ✅ |
| **EXTENSION** | +2 | ⚠️ interaction_step_count, kernel_execution row |

### factory_gap 闭合（D 母本）

| target | D 实现 |
|--------|--------|
| block_decay_rate | MemoryBlock.decay_rate + metadata |
| block_created_at | created_at + trace_id 派生 |
| block_updated_at | updated_at + STORE_step ISO |
| block_version_seq | version + iteration_counter |

---

## 8. evolved 模块索引（D 独有）

| 模块 | Runbook 层 |
|------|-----------|
| `core/evolved/sigma_mapping.py` | Layer1 NORMALIZE |
| `core/evolved/store_step.py` | STORE ownership |
| `core/evolved/cognitive_hooks.py` | COGNIZE/DECIDE/STORE writers |
| `core/evolved/trace_emit.py` | Σ.T emission |
| `core/evolved/migration_runner.py` | 05_migration_executor IR |
| `docs/evolved/LAYER1_NORMALIZATION.ref.md` | 摘要 |
| `docs/evolved/step_01_mapping_table.ref.json` | Σ_REMAP IR |

**kernel 接线**: `core/kernel/kernel.py::_emit_evolved_observability`

---

## 9. 跨层依赖冻结表（EXTRACT 发现）

| ID | 依赖 | 严重度 | D 状态 |
|----|------|--------|--------|
| X1 | trace ↔ state | CRITICAL | ⚠️ 部分缓解（图重放） |
| X2 | SelfModel 混写 | HIGH | ❌ OPEN — 见审计 |
| X3 | observe 直读 memory | MEDIUM | ❌ OPEN — 见审计 |
| X4 | registry handler 字符串 | LOW | ✅ CONFIG |
| X5 | fast_path 跨轮缓存 | MEDIUM | ❌ OPEN，D fast_path_v3 加重 |

---

## 10. EXTRACT 结论

```
D 盘 Layer1 EXTRACT 完整，可作为 Runbook 母本 SSOT。

相对 F Runbook:
  + 路径 memory → kernel 已修正
  + evolved/ 提供 factory_gap 运行时闭合
  + side-channel 投影不污染 v1 schema
  - X2/X3 仍 OPEN
  - NORMALIZE 中 trace 分片 / trace_id 格式未落地
  - SANDBOX 产品级 BOOT 未在本 EXTRACT 范围

下一步（迁移施工，非 EXTRACT）:
  1. X2 三域持久化拆分
  2. X3 observe 改 ExecutionRecordView / Σ.T adapter
  3. Layer2 trace 纯化（按日分片可选）
```
