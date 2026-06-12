# CNexus 持久记忆（Project Persistent Memory）

**产品线：** CNexus — Observational Cognition Platform  
**工作路径：** `D:\类脑记忆\CNexus — Observational Cognition Platform`  
**最后更新：** 2026-06-12  
**文档版本：** v0.2  
**状态：** L1 Memory Infrastructure 四步完成 + 中期 Block 类型化 v0.1

---

## 一、项目愿景

### 核心定位

CNexus 是位于 **Foundation Model（LLM）之下**、与**人类用户**之间的 **持久认知运行时（Persistent Cognitive Runtime）**。

目标不是让 AI 更聪明，而是让 AI **长期稳定地成为同一个存在**——解决传统 LLM「每次对话都像失忆」和「人格漂移」的根本问题。

### 设计哲学（不可违反）

| 原则 | 含义 |
|------|------|
| **Engineering First** | 所有功能可工程化、可测量、可验证 |
| **Observation ≠ Control** | 只读观察 + 治理，不直接控制底层模型 |
| **Stability-First** | 稳定性优先于功能丰富度 |
| **记忆独立于 LLM** | 记忆是认知基础设施，不是 Prompt 附属品；LLM 只负责推理，存储/召回/更新/生命周期由 L1 外部系统负责 |
| **边界约束** | 严格避开意识、灵魂、Qualia；只做认知连续性系统 |

### 核心维度

**已确认：** 认知 · 人格 · 记忆 · 情感 · 意向性

**待扩展：** 社会认知（Theory of Mind）· 价值观与道德框架 · 动机与驱动 · 元认知 · 注意力与资源分配 · 叙事连续性强化

### 最终愿景

构建具备持久记忆、稳定人格、情感与意向驱动、社会认知和道德边界的 **长期 AI 伙伴系统**，让人类与之交互时感受到「同一个存在」在持续进化。

### 宪法定位（冻结）

> CNexus 是一个多存储认知治理 sidecar：runtime 持有现实写权限；CDG 提供 advisory control；audit 是 projection；L7 是 post-hoc health observer；GTBS 正在逐步引入 transaction boundary。

详见：`docs/architecture/Constitutional_Semantics_v1.md`

---

## 二、架构对账结论（2026-06-12）

### 层号对齐（代码 vs 设计文档）

| 设计文档层号 | 代码实际（`brain_memory/runtime.py`） |
|-------------|--------------------------------------|
| L1 Memory Infrastructure | Layer 1 — Storage + **MemoryManager** |
| L2 Cognitive Runtime | Layer 2 — Cognitive Runtime (`runtime/`) |
| L3 Personality & Affective-Intentional | Layer 3 — Personality (`core/personality/`) |
| L4 Reflection & Metacognition | Layer 3.5 — Reflective (`core/personality/reflective/`) |
| L5 Governance & Audit | Layer 4 Stability + L6 CDG + L7/L8 (`core/governance/`) |
| Observation Layer | `core/observation/`（独立横切） |
| Validation Layer | `core/validation/`（独立横切） |

### 成熟度总账（对账时 52 项）

| 状态 | 数量 | 说明 |
|------|------|------|
| EXISTS | 29 | 骨架高度吻合 |
| PARTIAL | 19 | 名称/位置偏差或功能分散 |
| MISSING | 7 | 关键能力缺口 |

### 各层成熟度

| 层 | 成熟度 | 要点 |
|----|--------|------|
| L1 Memory | ★★★★☆ | **2026-06-12 大幅提升** — MemoryBlock + Manager + 召回 + 生命周期已落地 |
| L2 Cognitive | ★★★★☆ | Router/Recall/Attention/Context 完整；LLM Adapter 未接入主循环 |
| L3 Personality | ★★★☆☆ | DNA/信念/叙事/反思完整；**EmotionEngine + IntentEngine 缺失** |
| L4 Reflection | ★★★☆☆ | ReflectionPipeline 存在；Sleep-time Compute 缺失 |
| L5 Governance | ★★★★★ | GTBS / Semantic Safety / L8 UnifiedKernel 最成熟 |
| Observation | ★★★★★ | Gateway / Normalizer / L2 Streaming / Adapters 完整 |
| Validation | ★★★★☆ | Orchestrator + 漂移/身份/叙事评分完整 |
| External Interfaces | ★★★☆☆ | REST/WS/Web UI 有；入站 OpenAI API / SKILL / Desktop 缺 |

### 三大系统性差距（当前状态）

#### 差距 1：助手闭环未接线 — 🟢 已解决（2026-06-12）

```
[默认] /chat (full_cognitive_loop=true) → process_interaction() → reply + coherence_score + meta_reflection
[兼容] /chat (full_cognitive_loop=false) → recall → LLMClient → capture（轻量旁路）
```

- `brain-memory-ui/api/routes/chat.py` 默认走完整认知闭环
- `process_interaction()` 支持 `llm_client` + `llm_profile` 生成回复，并返回 `coherence_score` / `emotion_state` / `active_intent`

#### 差距 2：Memory Block 抽象缺失 — 🟢 已基本解决（2026-06-12）

L1 四步完成后，`MemoryBlock` + `MemoryManager` + `MemoryBlockStore` + 按 label 召回 + 生命周期均已落地。`Memory`（episodic 流水）与 `MemoryBlock`（结构化状态）并存。

#### 差距 3：Emotion + Intent 引擎 — 🟢 已解决（2026-06-12）

- **EmotionEngine** — `core/personality/emotion_engine.py` → `emotion` MemoryBlock
- **IntentEngine** — `core/personality/intent_engine.py` → `intent` MemoryBlock（目标追踪 + 动机 + 主动触发）

### 命名映射表（设计 → 代码）

| 设计名称 | 代码实际 |
|---------|---------|
| Memory Manager | `MemoryManager` (`memory/manager.py`) |
| MemoryBlockStore | `MemoryBlockStore` (`memory/block_store.py`) |
| HierarchicalRecallEngine | `HierarchicalRecallEngine` (`runtime/router.py`，`HierarchicalRecallRouter` 为别名） |
| CognitiveParser | `CognitiveStateParser` |
| PredictiveLoop | `PredictiveSelf` |
| LLM Adapter | `LLMClient` (`core/llm_client.py`) |
| ReflectiveEngine | `ReflectionPipeline` |
| process_message | `process_interaction()` |
| Governance Hook | `BlockGovernanceHook` + `MemoryWriteGate` |

### 仍缺失模块

- ~~`EmotionEngine` / `IntentEngine`~~（已落地）
- ~~`dialogue_trace` Memory Block~~ → **中期已类型化**（`episodic_dialogue` / `DecisionTraceBlock`，见 `docs/CNexus_Block_Typing_Evolution_v0.1.md`）
- `Sleep-time Compute`（部分：`sleep_time_compute.py` 已接 episodic block 合并）
- 入站 OpenAI 兼容 API / SKILL 规范 / Desktop App（OpenAI + v1 REST 已落地）
- ~~`coherence_score` 统一输出~~（`process_interaction` 已返回）

### 中期 Block 类型化（v0.2 新增）

| 能力 | 位置 |
|------|------|
| `BlockType` + label alias | `memory/block.py` |
| `update_from_field()` | `AttentionStateBlock` |
| Episodic 三元组 append + graph link | `MemoryBlockStore.add_episodic_triple()` |
| Recall 优先级表 | `RECALL_PRIORITY_RANK` + `label_recall_priority()` |
| 迁移 dry-run / group-triples | `scripts/migrate_episodic_blocks.py` |

---

## 三、当前 L1 架构（2026-06-12 落地态）

```
L1: Memory Infrastructure Layer
│
├── MemoryManager (memory/manager.py)          ← 唯一记忆入口
│   ├── create_block / update_block / delete_block
│   ├── capture_interaction()                  ← 双写：episodic + block
│   ├── recall_blocks() / get_core_context_blocks()
│   ├── protect_block() / compress_archival_blocks()
│   └── run_maintenance()                      ← block + episodic 维护
│
├── MemoryBlockStore (memory/blocks/)
│   ├── {block_id}.json                        ← 当前状态
│   ├── versions/{block_id}/v{n}.json            ← 版本历史
│   ├── index.json
│   └── provenance.jsonl
│
├── BlockGovernanceHook
│   ├── approved / flagged / rejected
│   └── Consistency 只标记，WriteGate 才拦截
│
├── BlockLifecycleManager (memory/lifecycle.py)
│   ├── apply_decay（按 label × idle_days）
│   ├── should_forget（core 永不遗忘）
│   └── compress_archival
│
├── HierarchicalRecallEngine (runtime/router.py)
│   ├── recall_blocks() — 按 label 优先级
│   └── recall_episodic() — 旧 Memory 向量召回（兼容）
│
└── Storage Layer
    ├── LanceDB — episodic 向量
    ├── Kuzu — 关系图
    └── JSON — MemoryBlock 持久化
```

### MemoryBlock 类型（6 类）

| label | 用途 | 常驻上下文 | decay_rate | auto_protected |
|-------|------|-----------|------------|----------------|
| persona | 人格 + 叙事自我 | 是 | 0.0 | ✅ |
| intent | 当前目标与动机 | 是 | 0.005 | ✅ |
| emotion | 当前情感状态 | 是 | 0.01 | — |
| working_memory | 当前任务关键信息 | 是 | 0.02 | — |
| user_profile | 用户长期偏好 | 按需 | 0.008 | — |
| archival_facts | 长期事实与经验 | 否 | 0.03 | — |

**召回优先级：** persona > intent > user_profile > emotion > working_memory > archival_facts

### Layer → Block 捕获路由

| layer | block |
|-------|-------|
| identity | persona |
| goal | intent |
| working | working_memory |
| relationship | user_profile |
| meta.block_label | 显式指定 |

---

## 四、2026-06-12 更新记录

### 工作区

- 文件夹更名为：`D:\类脑记忆\CNexus — Observational Cognition Platform`（原 `cursor`）
- 已同步：`.cursor/rules/workspace-root.mdc`、`docs/DEPLOYMENT.md` 等路径引用

### L1 第一步：MemoryBlock 数据模型 + CRUD

**新增文件：**
- `memory/block.py` — MemoryBlock 模型 + BLOCK_SPECS + LABEL_PRIORITY
- `memory/block_store.py` — CRUD + 版本控制 + provenance
- `memory/governance_hook.py` — BlockGovernanceHook
- `memory/manager.py` — MemoryManager 统一入口
- `tests/test_memory_blocks.py`

**Runtime 接入：** `runtime.memory_manager` / `runtime.memory`

### L1 第二步：capture 路由 + Governance 强化

- `MemoryManager.capture_interaction()` — episodic 双写 + block 路由
- `_commit_capture()` 改调 MemoryManager
- `return_detail=True` 返回完整 dict；默认仍返回 `episodic_id`（向后兼容）
- Governance：`approved` / `flagged`（标记但写入）/ `rejected`

### L1 第三步：按 label 分层召回

- `runtime/router.py` 重构为 `HierarchicalRecallEngine`
- `hybrid_recall()` = `recall_blocks()` + `recall_episodic()`
- `runtime/cognitive_recall.py`、`runtime/context.py` 支持 `_source=block`
- `tests/test_recall_blocks.py`（10 项）

### L1 第四步：Block 生命周期管理

**MemoryBlock 新字段：** `last_accessed_at`、`decay_factor`、`decay_rate`、`protected`

**新增：**
- `BlockLifecycleManager` + `BlockMaintenanceReport`（`memory/lifecycle.py`）
- `MemoryManager.protect_block()` / `compress_archival_blocks()` / `run_maintenance()`
- `runtime.maintain_memory()` — 手动维护入口
- `tests/test_block_lifecycle.py`（10 项）

### 测试状态

L1 相关测试合计 **43+ 项全通过**（memory_blocks + recall_blocks + block_lifecycle + integration）。

---

## 五、开发优先级（下一步）

| 优先级 | 任务 | 状态 |
|--------|------|------|
| P0 | 将 `/chat` 接入 `process_interaction()` 完整闭环 | ✅ 已完成 |
| P1 | ValuesGovernance + `value_alignment_history` block | ✅ 已完成 |
| P1b | ~~EmotionEngine + IntentEngine~~ | ✅ 已完成 |
| P2 | Sleep-time Compute（`core/memory/sleep_time_compute.py`） | ✅ 已完成 |
| P3 | ReflectiveEngine LLM 增强（Reflexion JSON + 规则降级） | ✅ 已完成 |
| P4 | IntentEngine 主动行为闭环（proactive trigger + /chat） | ✅ 已完成 |
| P5 | 入站 OpenAI 兼容 API + SKILL 规范 | ✅ 已完成 |
| P6 | 多平台 LLM Adapter 深化（Anthropic 原生等） | 待做 |
| P3 | `value_alignment_history` / `dialogue_trace` Block | 待做 |
| P4 | Sleep-time Compute（异步记忆整理） | 待做 |
| P5 | Desktop App（Tauri） | 待做 |

---

## 六、关键入口速查

```python
# Runtime
from brain_memory import create_runtime
runtime = create_runtime()

# L1 Memory
runtime.memory.create_block("persona", "稳定、理性、工程优先")
runtime.memory.get_active_block("intent")
runtime.memory.get_core_context_blocks()
runtime.capture("user", "长期目标...", layer="goal")  # 双写
runtime.recall("我的身份和目标")                        # 含 Structured Memory Blocks
runtime.maintain_memory(force=True)                     # 生命周期维护

# 治理
runtime.run_governance_cycle()  # 含 memory_maintenance
runtime.process_interaction(user_input, assistant_output=...)  # 完整闭环
# HTTP: POST /chat { full_cognitive_loop: true }  # 默认已接线
```

**推荐 API：** `brain-memory-ui/api/` (:8000) — REST + WebSocket  
**遗留 API：** `api/server.py` (:8080) — 静态 UI，已 deprecated

---

*本文档为 CNexus 项目级持久记忆，供开发者与 AI Agent 跨会话保持上下文一致性。*
