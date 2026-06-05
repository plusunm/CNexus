---
name: brain-memory-tools
description: 大脑记忆 v5.0 — Cognitive Stability | Deterministic Router + Belief + Reflection
version: 5.0.0
tags: [memory, brain, belief, reflection, goal-lifecycle, deterministic-router, stability]
---

# brain-memory-tools v5.0

**描述**：OpenClaw 类脑长期记忆 — v5.0 Cognitive Stability Architecture。

## 工具列表

| 工具 | 说明 |
|------|------|
| `brain_recall(query, top_k=12, use_hyde=true)` | Deterministic Router + HyDE + 图扩展 |
| `brain_recall_detail(query)` | context + route + provenance（JSON） |
| `brain_reflect()` | Meta-Memory 反思引擎 |
| `brain_update_goal(goal, importance=0.88, status="active")` | Goal Lifecycle 写入 |
| `brain_store(role, content, layer="episodic")` | 存储（CaptureFilter + Write Gate + Belief Check） |
| `brain_consolidate()` | 睡眠巩固 + v5.0 代谢循环 |
| `brain_stats()` | 含 belief_count / self_stability / recall_routes |
| `brain_layer_stats()` | 含 meta 层分布 |

（其余工具同 v4.x：multi-hop、provenance、forget、export 等）

## v5.0 路由类型

`short_term` | `goal` | `semantic` | `reflect` | `archive` | `graph_reasoning` | `episodic`

## 配置（openclaw.json）

```json
{
  "plugins": {
    "entries": {
      "brain-memory": {
        "config": {
          "write_gate_threshold": 0.45,
          "attention_half_life": 3600,
          "belief_compat_threshold": 0.72,
          "reflection_enabled": true,
          "enable_metabolic": true
        }
      }
    }
  }
}
```

Plugin 自动：`before_agent_start` recall、`agent_end` capture。
