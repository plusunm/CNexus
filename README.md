# Brain-Memory v5.0

**Persistent Cognitive Runtime for AI Agents**  
**AI Personality Continuity Infrastructure**

---

## 项目定位

Brain-Memory v5.0 不是普通的记忆插件，也不是通用 Agent 框架。

它是一个**为无状态大模型设计的长期人格连续性基础设施**，目标是让 AI 在长期运行中**保持人格、信念、叙事和行为的连续一致性**，实现**可控的稳定演化**。

**核心使命**：  
**让 AI 长期稳定地成为同一个存在**。

---

## 核心特性

### 五层 + Validation 架构
- **Layer 1 Memory Infrastructure**：多层记忆 + LanceDB + Kuzu + Provenance
- **Layer 2 Cognitive Runtime**：Hierarchical Router + Dynamic Attention + State Manager
- **Layer 3 Personality Continuity**：Personality DNA + Narrative Self + Belief Governance
- **Layer 4 Stability Governance**：Drift Detection + Homeostasis + Anchoring
- **Layer 5 Governance & Safety**：Write Gate + Constitution + Audit
- **Validation & Observability Layer**：Long-term Simulation + Metrics + Dashboard

### 神经科学映射
- Filtering（丘脑） + Deduplication（齿状回） + Distillation（睡眠巩固） + Reconsolidation + Physical Forgetting

### 关键能力
- Deterministic Router（避免 LLM 漂移）
- Dynamic Attention Field（7±2 Working Memory）
- Mutation Guard + Constitution Enforcement
- Full Governance Audit Trail
- Stability Validation Suite

---

## 快速开始

### 安装
```bash
cd D:\类脑记忆\cursor
pip install -r requirements.txt
ollama pull nomic-embed-text
ollama pull llama3.2
```

### 基本使用
```python
from brain_memory import BrainMemoryRuntime

runtime = BrainMemoryRuntime(config_path="config/default.json", project_root=".")

runtime.capture("user", "我希望长期构建稳定的人格 AI 系统", layer="goal")
context = runtime.recall("我的长期目标是什么？")
print(context)

runtime.run_governance_cycle()  # 稳定性治理
```

---

## 项目架构

```
brain-memory/
├── config/           # 配置中心
├── core/             # 人格、治理、验证核心
├── memory/           # 记忆 Schema + 过滤
├── storage/          # LanceDB + Kuzu 存储
├── runtime/          # 认知运行时
├── brain_memory/     # 主入口 BrainMemoryRuntime
├── api/              # FastAPI 接口（可选）
├── tests/            # 测试套件
└── docs/             # 文档
```

---

## Roadmap

- **v5.0**：Stability Core + Validation Program（已完成）
- **v6.0**：Controlled Evolution（Stable Personality Evolution）
- **v7.0**：Advanced Multi-Agent Federation

---

## 许可证与贡献

MIT License。欢迎对 **Cognitive Stability** 有兴趣的开发者共同推进。

**Brain-Memory v5.0**  
**不是让 AI 更聪明，而是让 AI 长期稳定地成为同一个存在。**
