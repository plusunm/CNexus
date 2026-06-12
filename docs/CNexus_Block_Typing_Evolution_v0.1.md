# CNexus 中期 Block 类型化演进 v0.1

**日期**：2026-06-12  
**状态**：已对齐现有 Pydantic 实现（非 dataclass 替换）  
**原则**：Stability-First · 向后兼容 · facade / HierarchicalRecall / BLOCK_SPECS 不破坏

## 与草稿的差异

| 草稿 | 当前实现 |
|------|----------|
| `@dataclass MemoryBlock` | **Pydantic** `MemoryBlock`（存储/治理/生命周期兼容） |
| `dialogue_trace` / `decision_trace` label | 规范 label：`episodic_dialogue` / `episodic_decision`（`BlockType` + alias 归一化） |
| `BLOCK_SPECS` → class map | `BLOCK_SPECS`（元数据 dict）+ `_BLOCK_CLASS_MAP`（类型工厂） |
| `user_id` Scoped store API | 全局 singleton blocks + `metadata.user_id` 可选过滤 |

## 新增类型注册

- `BlockType` enum — 所有 canonical label + `normalize_block_label()`
- `RECALL_PRIORITY_RANK` + `label_recall_priority()` — float rank table（BlockType 对齐，attention=0.90）
- `MemoryBlock.provenance_hash` — 可选，对接 storage provenance

## 独立 Block 类型

### AttentionStateBlock

- `sync_from_dynamic()` — 原有 hybrid 快照
- **`update_from_field()`** — DynamicAttentionField 委托入口（含 `dynamic_field` / `priority`）
- `validate()` / `to_context_string()` / `edit_via_tool()`

### Episodic 三元组

| 类 | Label | 辅助 API |
|----|-------|----------|
| `EpisodicEventBlock` | `episodic_event` | `event_type`, `link_blocks()`, `set_graph_edge()` |
| `DialogueTraceBlock` | `episodic_dialogue` | `session_id`, `turns`, `summary` |
| `DecisionTraceBlock` | `episodic_decision` | `decision_id`, `intent`, `reasoning`, `outcome`, `linked_reflection` |

## MemoryBlockStore 工厂

```python
store.get_attention_state(user_id=None)          # DynamicAttentionField 查询
store.sync_attention_from_dynamic(...)           # 内部调用 update_from_field
store.add_episodic_triple(event, dialogue, decision, session_id=..., link=True)
store.create_block(label, content, **kwargs)     # label alias 自动归一化
```

## MemoryManager Facade

```python
manager.get_attention_state(user_id)
manager.add_episodic_triple(...)
manager.link_episodic_chain(event_id=..., dialogue_id=..., decision_id=...)
```

## HierarchicalRecallEngine

- 排序/打分使用 `label_recall_priority(label)`（attention_state 提升至 0.90 rank）
- `recall_episodic_typed()` 不变

## 迁移

```bash
python scripts/migrate_episodic_blocks.py --dry-run
python scripts/migrate_episodic_blocks.py --dry-run --group-triples --user-id u123
python scripts/migrate_episodic_blocks.py --no-dry-run --group-triples
```

`--group-triples`：按 event → dialogue → decision 顺序写入 `add_episodic_triple()`。

## 演进约束

- `process_interaction()` / BrainMemoryRuntime facade **签名与主链路不变**
- 新 Block 通过迁移脚本或 capture 双写启用
- Governance Hook + provenance.jsonl 自动覆盖新 block 事件
- 旧 episodic vector/graph 层在迁移完成前继续工作

## 测试

```bash
python -m pytest tests/test_block_evolution.py -q
```

**文档版本**：v0.1 · **代码状态**：已落地（2026-06-12）
