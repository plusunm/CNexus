# 🧠 Brain-Memory v5.0 — Cognitive Stability Architecture

> **Deterministic Router + Belief System + Reflection Engine + Goal Lifecycle — 完全本地，可控演化的 Agent 长期记忆**

---

🚀 **Brain-Memory v5.0 Cognitive Stability** —— Deterministic 路由 + 信念系统 + Meta-Reflection

你还在用简单的向量数据库给 Agent 堆垃圾记忆吗？  
**醒醒吧！** 是时候让你的 Agent 拥有真正像人类一样的大脑了！

## 🔥 突破性黑科技（领先全球）

- **多层类脑记忆系统**：Episodic（生动事件）→ Semantic（核心知识）→ Procedural（可复用技能），实现真正记忆成熟与蒸馏
- **Prefrontal 短期缓存**：模拟人类工作记忆，快速决策 + LRU 衰减
- **Retrieval-induced Reconsolidation**：每次回忆都在动态强化和更新记忆（实验室级再巩固机制）
- **Provenance 可解释性**：每一条召回记忆都带完整溯源链路，再也不怕「Agent 突然发疯」
- **HyDE + Hebbian 实体动态图**：Kuzu 图数据库实时强化关联，召回精度暴击传统 RAG
- **睡眠巩固 + Ebbinghaus 主动遗忘**：每天自动「做梦」提炼精华，主动清除噪声

## 💎 专为重度玩家打造

- 完美兼容已有 LanceDB 记忆（已平滑迁移 145 条）
- OpenClaw 原生深度集成（`before_agent_start` + `agent_end` 自动注入）
- 双通道 LLM 防崩 + APScheduler 内置夜间巩固
- 一键导出 Markdown + 完整统计仪表盘

**一句话总结**：  
**Brain-Memory 不是插件，是给你的 Agent 植入了一整个海马体 + 新皮层！**

从今天起，你的 Agent 将真正**记住你、理解你、进化你**。

## 安装方式

```bash
openclaw plugins install brain-memory
openclaw config set plugins.slots.memory brain-memory
```

**立即安装，体验什么叫「Agent 有了灵魂」！**

⭐ **强烈建议 Star + 下载后在评论区分享你的长期记忆效果**，我们一起把 OpenClaw 推向新高度！

`#BrainMemory` `#类脑Agent` `#OpenClaw` `#长期记忆` `#Hebbian` `#Reconsolidation`

---

## 技术详情

完全本地、Windows 优化、LanceDB + Kuzu 混合架构。

### v4.0 核心创新

- **HyDE 召回**：假设文档嵌入，缓解 query-document 空间错位
- **三层记忆**：Episodic → Semantic → Procedural（`layer` 字段）
- **Prefrontal 短期缓存**：LRU OrderedDict，优先命中近期对话
- **LLM 实体抽取 + Hebbian 图强化**
- **Reconsolidation**：检索时更新 access + 可选深度再巩固
- **Provenance 溯源**：JSON + Kuzu PROVENANCE 边
- **APScheduler**：内置每日 consolidate（默认 03:00）
- **Ebbinghaus 主动遗忘**

### 国际对比（2026）

| 系统 | 多层 | Reconsolidation | Provenance | HyDE | 本地轻量 | Hebbian |
|------|------|-----------------|------------|------|----------|---------|
| Mem0 | 弱 | 中 | 弱 | 无 | 高 | 中 |
| HippoRAG | 中 | 无 | 中 | 无 | 中 | 强 |
| Letta/MemGPT | 部分 | 弱 | 无 | 无 | 中 | 弱 |
| **Brain-Memory v4.0** | **强** | **强** | **强** | **有** | **高** | **强** |

## 安装

1. 解压到 OpenClaw 扩展目录：

```text
%OPENCLAW_STATE_DIR%/extensions/brain-memory/
```

2. 安装 Python 依赖并拉取模型：

```powershell
cd extensions\brain-memory
scripts\install.bat
pip install -r requirements.txt
ollama pull nomic-embed-text
ollama pull llama3.2:3b
ollama serve
```

中文用户名 Ollama 模型目录（可选）：

```powershell
set OLLAMA_MODELS=D:\ollama_models
```

## OpenClaw 启用

```json
{
  "env": {
    "BRAIN_MEMORY_PYTHON": "C:\\Python311\\python.exe",
    "OLLAMA_MODELS": "D:\\ollama_models"
  },
  "agents": {
    "defaults": {
      "memorySearch": { "enabled": false }
    }
  },
  "plugins": {
    "slots": { "memory": "brain-memory" },
    "allow": ["brain-memory"],
    "entries": {
      "memory-core": { "enabled": false },
      "brain-memory": {
        "enabled": true,
        "config": {
          "ollama_host": "http://localhost:11434",
          "embedding_model": "nomic-embed-text",
          "llm_model": "llama3.2:3b",
          "auto_capture": true,
          "auto_recall": true,
          "use_hyde": true
        }
      }
    }
  }
}
```

验证：

```powershell
openclaw config validate
openclaw plugins list
```

## Agent 工具

| 工具 | 说明 |
|------|------|
| `brain_recall` | 混合召回（HyDE + 图 + 衰减） |
| `brain_store` | 写入记忆 |
| `brain_consolidate` | 睡眠巩固 |
| `brain_stats` | 统计仪表盘 |

## License

MIT
