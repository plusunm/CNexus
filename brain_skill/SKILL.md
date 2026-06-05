---
name: brain-memory-tools
description: 大脑记忆 v4.0 — HyDE + 多层记忆 + Provenance 可解释性 + Hebbian 图增强
version: 4.0.0
tags: [memory, brain, hyde, hebbian, provenance, consolidation, multi-layer]
---

# brain-memory-tools v4.0

**描述**：OpenClaw 类脑长期记忆工具集 — 与 memory slot 插件双保险（自动 + 显式）。

## 工具列表

| 工具 | 说明 |
|------|------|
| `brain_recall(query, top_k=12, use_hyde=true)` | 混合检索（默认 HyDE） |
| `brain_hyde_recall(query)` | 强制 HyDE 召回 |
| `brain_recall_detail(query)` | 返回 context + provenance + items（JSON） |
| `brain_store(role, content, layer="episodic")` | 存储（episodic/semantic/procedural） |
| `brain_extract_entities(content)` | LLM 实体关系抽取 |
| `brain_hebbian_strengthen(mem_id, content)` | 实体驱动 Hebbian 边强化 |
| `brain_consolidate()` | 多层睡眠巩固 → Semantic 摘要 |
| `brain_forget(dry_run=true)` | 主动遗忘（先 dry_run 预览） |
| `brain_provenance(mem_id)` | 记忆溯源链 |
| `brain_search_time(start_iso, end_iso)` | 时间范围搜索 |
| `brain_layer_stats()` | 各层记忆分布 |
| `brain_stats()` | 健康度统计 |
| `brain_export()` | Markdown 完整导出 |
| `brain_backfill(path)` | 从 chat_history.db 回填 |

## 使用规则（实验室标准）

1. **思考前**：`brain_recall` 或 `brain_hyde_recall`
2. **关键决策后**：`brain_store(..., layer="semantic")` 存偏好/事实
3. **技能/流程模式**：`layer="procedural"`
4. **每日 / 用户要求**：`brain_consolidate`
5. **可解释性**：用 `brain_provenance` 说明结论来源
6. **膨胀治理**：`brain_forget(dry_run=true)` → 确认 → `dry_run=false`

## OpenClaw 配置

```json
{
  "plugins": {
    "slots": {
      "memory": "brain-memory"
    }
  }
}
```

Plugin 自动：`on_message` 捕获、`before_llm_call` HyDE 注入。
