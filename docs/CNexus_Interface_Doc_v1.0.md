# CNexus 接口文档 v1.0

**版本**：v1.0  
**日期**：2026-06-12  
**依据**：架构 v1.0 + block 演进 + v1 REST facade

## 1. 统一入口

| 组件 | 路径 | 说明 |
|------|------|------|
| Runtime Facade | `brain_memory/runtime.py` → `BrainMemoryRuntime` | 认知主循环 |
| Legacy UI API | `api/server.py` | FastAPI + 静态 UI |
| Runtime API | `brain-memory-ui/api/main.py` | 解耦 UI / Desktop / Mobile |
| v1 Spec 层 | `api/v1_endpoints.py` | `/v1/*` 规范端点 |
| OpenAI 兼容 | `api/openai_compatible.py` | `/v1/chat/completions` |

启动示例：

```bash
# Legacy UI
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000

# Runtime API（含 WebSocket）
python -m uvicorn brain-memory-ui.api.main:app --host 0.0.0.0 --port 8080
```

## 2. REST Endpoints

Base path: `/v1`

### POST /v1/interact

主交互入口，封装 `BrainMemoryRuntime.process_interaction()`。

**请求**

```json
{
  "user_id": "u123",
  "message": "你好",
  "session_id": "s456",
  "metadata": {"session_id": "s456"},
  "context": {},
  "options": {
    "use_memory": true,
    "temperature": 0.7,
    "governance_level": "normal"
  }
}
```

`metadata.session_id` 与顶层 `session_id` 等价；若仅提供 `metadata.session_id` 会自动归一化。

**响应**

```json
{
  "response": "你好！今天过得怎么样？",
  "provenance_id": "cap-abc123",
  "provenance": {
    "trace_id": "cap-abc123",
    "blocks_used": ["persona", "working_memory", "attention_state", "emotion"]
  },
  "attention_state": {
    "focus": "persona, working_memory",
    "priority": 4,
    "focus_scores": {"persona": 0.82}
  },
  "governance_pass": true,
  "memory_blocks_updated": ["attention_state", "emotion", "persona"],
  "enriched_context": {},
  "meta": {"user_id": "u123", "session_id": "s456"}
}
```

### GET /v1/status

运行时状态（CLI `python -m brain_memory status` 的 HTTP 等价）。

**别名**：`GET /v1/state`（同一实现）

**响应字段**：`blocks_summary`、`attention_state`、`governance`、`full_status`

### POST /v1/capture

带 metadata 的记忆捕获（会话 / 用户上下文）。

```json
{
  "user_id": "u123",
  "role": "user",
  "content": "今天完成了接口对齐",
  "layer": "episodic",
  "importance": 0.65,
  "metadata": {"session_id": "s456", "source": "manual"}
}
```

**响应**：`{"memory_id": "...", "status": "success", "block_label": "episodic_event"}`

### GET /v1/memory/blocks

列出活跃 MemoryBlock；可选 `?label=persona`。

### POST /v1/memory/recall

分层 recall 调试：`{"query": "...", "top_k": 8, "include_episodic": true}`

### GET /v1/governance/audit

CDG 轨迹只读视图。

### POST /v1/governance/check

运行一次稳定性治理周期。

## 3. WebSocket

| 路径 | 用途 |
|------|------|
| `ws://host/ws/interact` | 规范交互流（attention 增量 + done） |
| `ws://host/ws/chat` | 轻量 LLM 对话（legacy UI） |
| `ws://host/ws/state` | 状态推送（约 2s 间隔） |

### ws://host/ws/interact

**客户端发送**（与 POST /v1/interact 相同 JSON）：

```json
{"user_id": "u123", "message": "你好", "metadata": {"session_id": "s456"}}
```

**服务端推送**：

1. `{"type": "attention", "attention_state": {...}}`
2. `{"type": "done", ...InteractResponse...}`

错误：`{"type": "error", "error": "..."}`

## 4. OpenAI Compatible

### POST /v1/chat/completions

标准 OpenAI Chat Completions 形态，扩展 CNexus 字段：

**请求扩展**（任选其一）：

```json
{
  "model": "cnexus-cognitive",
  "messages": [{"role": "user", "content": "你好"}],
  "metadata": {
    "user_id": "u123",
    "session_id": "s456",
    "enable_memory": true
  },
  "cnexus": {
    "user_id": "u123",
    "enable_memory": true,
    "persona_block": "..."
  }
}
```

OpenAI Python SDK：

```python
client.chat.completions.create(
    model="cnexus-cognitive",
    messages=[{"role": "user", "content": "你好"}],
    extra_body={"cnexus": {"user_id": "u123", "enable_memory": True}},
)
```

**响应扩展**：

- `cnexus`：运行时元数据（model、coherence、emotion 等）
- `cnexus_provenance`：`{"trace_id", "blocks_used", "user_id", "session_id"}`

## 5. CLI / SDK

```bash
# 状态
python -m brain_memory status

# 单次交互
python -m brain_memory interact --user-id u123 --session-id s456 "你好"

# 治理
python -m brain_memory governance --json
```

Python SDK：

```python
from brain_memory import create_runtime

runtime = create_runtime(project_root=".")
result = runtime.process_interaction("你好", use_memory=True)
context = runtime.recall("最近讨论了什么？")
```

## 6. 验证路径

- 对话链路：`recall()` → attention sync → `ContextAssemblyEngine` 注入 `【Attention State】` + `【Episodic Traces】`
- Block 演进测试：`python -m pytest tests/test_block_evolution.py -q`
- v1 接口测试：`python -m pytest tests/test_v1_endpoints.py -q`
- Episodic 迁移 dry-run：`python scripts/migrate_episodic_blocks.py --dry-run`

## 7. 版本说明

| 项目 | 值 |
|------|-----|
| 文档版本 | v1.0 |
| 实现 commit 基线 | block 演进 + v1 REST facade |
| 下一步 | `docs/CNEXUS_PERSISTENT_MEMORY.md` 版本号与示例同步 |
