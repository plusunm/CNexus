# CNexus 接口文档 v1.1

**版本**：v1.1  
**日期**：2026-06-12  
**依据**：ARCHITECTURE.md v1.0 + 请求处理主链路 + 接口示例补充  
**核心原则**：Engineering First、Observation ≠ Control、Stability-First、L5 可拦截/修订、L1 统一记忆、LLM Adapter 仅生成  
**代码状态**：已落地（2026-06-12）

---

## 1. 统一入口

| 组件 | 路径 | 说明 |
|------|------|------|
| Runtime Facade | `brain_memory/runtime.py` → `BrainMemoryRuntime` | L1→L5 初始化 |
| Legacy UI API | `api/server.py` | FastAPI + `/ws/interact` |
| v1 REST | `api/v1_endpoints.py` | `/v1/*` 规范端点 |
| OpenAI 兼容 | `api/openai_compatible.py` | 注入 `cnexus` extra_body |
| Runtime API | `brain-memory-ui/api/main.py` | UI 解耦 API |
| WebSocket 共享 | `api/ws_routes.py` | `/ws/interact` |
| CLI | `brain_memory/__main__.py` | `status` / `interact` / `governance` |

**关键调用**：

```python
from brain_memory import BrainMemoryRuntime

runtime = BrainMemoryRuntime.create_runtime(config_path="config/default.json")
result = runtime.process_interaction(
    message="你好，今天怎么样？",
    user_id="u123",
    metadata={"session_id": "s456", "enable_memory": True},
)
print(result["response"], result["attention_state"])
```

---

## 2. REST Endpoints

Base path: `/v1`

### POST /v1/interact

**请求**：

```json
{
  "user_id": "u123",
  "message": "我最近工作压力很大，有什么建议？",
  "metadata": {
    "session_id": "s456",
    "enable_memory": true,
    "persona_block": "default"
  }
}
```

**响应**：

```json
{
  "response": "我理解你的压力…",
  "provenance": {
    "trace_id": "cap-abc123",
    "blocks_used": ["persona", "emotion", "user_profile", "attention_state"],
    "episodic_layers": [3, 5],
    "governance": {
      "values_check": "passed",
      "cdg_intercept": false,
      "revision_note": null
    },
    "timestamp": "2026-06-12T12:00:00Z"
  },
  "attention_state": {
    "focus": "persona + emotion",
    "priority": 4,
    "dynamic_field": {"recent_topics": ["pressure", "suggestion"]}
  },
  "reflection_triggered": false,
  "governance_pass": true
}
```

**L5 修订**（`options.strict_governance_error: true` → HTTP 422）：

```json
{
  "error": "governance_intercept",
  "message": "请求被 L5 ValuesGovernance 修订",
  "revised_response": "抱歉，我无法提供该建议…",
  "provenance": {"governance": {"values_check": "revised", "reason": "…"}}
}
```

### GET /v1/status

```json
{
  "layers": {
    "memory_blocks": {"persona": 1, "attention_state": "dynamic"},
    "episodic": {"active_layers": 8, "total_events": 1247},
    "governance": {"drift_score": 0.02, "last_values_check": "2026-06-12T11:58:00Z"}
  },
  "attention": {"current_focus": "work_stress", "priority": 4},
  "stability": "healthy"
}
```

`GET /v1/state` 保留完整 `StateResponse`。

### POST /v1/capture

metadata 捕获（会话/事件），不触发生成。

---

## 3. WebSocket

**`ws://host/ws/interact`**

推送序列：

1. `{"type": "attention", "attention_state": {...}}`
2. `{"type": "delta", "delta": "<完整回复>"}` — 整段 delta（非 LLM token 流）
3. `{"type": "done", ...InteractResponse...}`

---

## 4. OpenAI Compatible

**POST /v1/chat/completions**

```json
{
  "model": "cnexus-cognitive",
  "messages": [{"role": "user", "content": "你好"}],
  "cnexus": {
    "user_id": "u123",
    "enable_memory": true,
    "session_id": "s456"
  }
}
```

响应扩展：`cnexus` + `cnexus_provenance`（含 governance）。

---

## 5. CLI / SDK

```bash
python -m brain_memory interact --user-id u123 "我最近工作压力很大，有什么建议？"
python -m brain_memory status
```

---

## 6. 验证

```bash
python -m pytest tests/test_block_evolution.py tests/test_v1_endpoints.py -q
python scripts/migrate_episodic_blocks.py --dry-run
```

**注意**：记忆经 L1 统一；L5 可拦截/修订；Observation Layer 只读 append-only。

**下一步**：Block 类型化见 `docs/CNexus_Block_Typing_Evolution_v0.1.md`（已落地）。
