# Brain-Memory v5.0 架构文档

## 五层 + Validation 架构

| 层级 | 目录 | 职责 |
|------|------|------|
| Layer 1 Memory Infrastructure | `memory/`, `storage/` | 多层记忆存储、向量检索、认知图谱 |
| Layer 2 Cognitive Runtime | `runtime/` | 分层召回、注意力场、状态管理 |
| Layer 3 Personality Continuity | `core/personality/` | DNA、叙事自我、信念治理 |
| Layer 4 Stability Governance | `core/governance/` | 漂移检测、身份锚定、稳态控制 |
| Layer 5 Governance & Safety | `core/governance/safety/` | 写入门控、宪法、审计 |
| Validation Layer | `core/validation/` | 长期模拟、回归测试、可观测性 |

## 核心数据流

```
Capture → CaptureFilter → WriteGate → Storage (LanceDB + Kuzu)
Recall  → Router → Attention → ContextAssembly → LLM Context
Governance → DriftDetector → IdentityAnchor → StabilityMetrics
```

## 设计原则

- **Stability First**：优先保障身份连续性
- **Persistent Identity**：DNA + Narrative + Anchoring
- **Controlled Evolution**：慢速变更 + Guard + Approval
- **Governance Deterministic**：规则驱动 + 可审计
