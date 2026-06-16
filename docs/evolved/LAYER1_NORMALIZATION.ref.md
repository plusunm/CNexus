# Layer 1 Normalization Reference (摘要)

> 源：`F:\CNexus — Observational Cognition Platform\NEW_CNEXUS\CNEXUS_MIGRATION_RUNBOOK_v3_PURIFIED\05_migration_executor\LAYER1_NORMALIZATION_RESULT.md`  
> D: 母本实现：`core/evolved/sigma_mapping.py` + `memory/block_store.py`

## 路径重定向

| F: 扫描路径 | D: 母本等价 |
|-------------|-------------|
| `core/memory/observe/record_store.py` | `memory/block_store.py` |
| `observe_record` | `MemoryBlock` + `ExecutionRecord` |

## FACTORY_GAP 闭合状态

| 字段 | Runbook | D: 母本 |
|------|---------|---------|
| `block_decay_rate` | FACTORY_GAP | ✅ `MemoryBlock.decay_rate` |
| `block_created_at` | FACTORY_GAP | ✅ `MemoryBlock.created_at` + trace 派生 |
| `block_updated_at` | FACTORY_GAP | ✅ `MemoryBlock.updated_at` + STORE_step |
| `block_version_seq` | FACTORY_GAP | ✅ `MemoryBlock.version` |
| `block_importance_snapshot` | partial | ✅ `state_projection.stability_metrics` + metadata |

## SelfModel Split Map

| Writer | 字段 | D: 实现 |
|--------|------|---------|
| COGNIZE_step | relationship_state, prediction_state | `core/evolved/cognitive_hooks.py` |
| DECIDE_step | identity_projection, behavioral_tendency | `core/evolved/cognitive_hooks.py` |
| STORE_step | block_updated_at, iteration_counter | `store_step.py` + `SelfModelStore.store_step_touch` |
