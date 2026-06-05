
  
🧠 Brain Memory

  
Local cognitive memory for AI agents.


  
Hebbian learning · Reconsolidation · HyDE retrieval · Local-first


  

    
    
    
    
  




---

## Your AI stops forgetting.

**Stop re-explaining your project to AI every day.**

Brain Memory gives your agents persistent long-term memory across sessions, projects, and coding workflows. It's not a vector database wrapper — it's a cognitive architecture that models how real brains learn, forget, and consolidate.

```bash
openclaw plugins install brain-memory
openclaw config set plugins.slots.memory brain-memory
```

---

## ✨ Why Brain Memory?

Most "AI memory" systems are just vector search with a UI. Brain Memory is fundamentally different:

| Feature | Brain Memory | mem0 | SimpleMem | Vector DB Only |
|---|---|---|---|---|
| **Hebbian Learning** (reinforcement) | ✅ | ❌ | ❌ | ❌ |
| **Reconsolidation** (update on recall) | ✅ | ❌ | ❌ | ❌ |
| **HyDE Retrieval** (hypothetical doc embedding) | ✅ | ✅ | ⚠️ | ❌ |
| **Multi-layer Memory** (Epi→Sem→Proc) | ✅ | ❌ | ❌ | ❌ |
| **Prefrontal Cache** (working memory) | ✅ | ❌ | ❌ | ❌ |
| **Ebbinghaus Forgetting** (decay) | ✅ | ❌ | ❌ | ❌ |
| **Sleep Consolidation** (nightly digestion) | ✅ | ❌ | ❌ | ❌ |
| **Provenance** (traceability per recall) | ✅ | ❌ | ❌ | ❌ |
| **Local-first** (zero cloud dependency) | ✅ | ⚠️ | ✅ | ✅ |
| **MCP / OpenClaw Native** | ✅ | ⚠️ | ⚠️ | ❌ |

---

## 🧬 Architecture

```
User Input
    ↓
    ├── Prefrontal Cache (LRU)
    │   Working memory — fast, ephemeral
    │
    ├── Extraction + Importance Scoring
    │   (LLM evaluates: keep? forget? level?)
    │
    ├──┐          ┌──┐
    │  LanceDB Vector  │  │  Kuzu Graph      │
    │  (HyDE + dense)  │  │  (Hebbian edges) │
    ├──┘          └──┘
    │
    ├── Hybrid Retrieval
    │   vector + graph + time
    │
    ├── Reconsolidation
    │   strengthen ↔ refresh
    │
    ├── Prompt Injection
    │   context → LLM call
    │
    └── Nightly: Sleep Consolidation → Ebbinghaus Decay
```

---

## 🚀 Quick Start

### Requirements
- Python 3.11+
- Ollama (with `nomic-embed-text` model)

### Install

```bash
# Install plugin
openclaw plugins install brain-memory

# Enable as default memory slot
openclaw config set plugins.slots.memory brain-memory

# (Or manual install)
git clone https://github.com/plusunm/brain-memory.git
cd brain-memory
pip install -r requirements.txt
```

### Verify

```python
from memory_backend import BrainMemoryBackend

memory = BrainMemoryBackend(auto_init=True)

# Store a memory
memory.capture(role='user', content='User prefers Chinese, uses Ollama locally')

# Recall relevant memories
results = memory.recall('What language does the user prefer?')
print(results)
```

---

## 🔥 Core Capabilities

### 1. Multi-layer Memory
Memories are automatically distilled across three layers — just like the human brain:
- **Episodic** — raw events, conversations, experiences
- **Semantic** — extracted facts, preferences, knowledge
- **Procedural** — reusable skills, workflows, patterns *(experimental)*

### 2. Hebbian Learning Graph
Entities automatically strengthen connections as they co-occur. "Cells that fire together wire together" — Kuzu graph DB persists these dynamic relationships.

### 3. Retrieval-induced Reconsolidation
Every recall rewrites the memory trace, strengthening or updating it. This prevents memory decay from simple re-reading and keeps knowledge fresh.

### 4. Prefrontal Cache
Working memory with LRU eviction. The most recent and important items stay hot for fast retrieval.

### 5. Sleep Consolidation
APScheduler-driven nightly digestion: summarizes high-importance memories, abstracts patterns, prunes noise.

### 6. Ebbinghaus Forgetting Curve
Low-importance memories decay over time. The system forgets what it doesn't need — just like you do.

### 7. Provenance
Every recall trace carries its full lineage: source, timestamp, layer, importance score, and Hebbian path.

---

## 🧹 Memory Governance

Most AI memory systems fail because they remember too much.

Brain Memory actively filters:
- noisy tool outputs
- duplicate recalls
- transient context
- low-value traces

The goal is not maximum storage. The goal is useful cognition.

---

## 📊 Benchmarks

*Preliminary internal benchmarks — methodology will be published with the next release.*

| Metric | Value |
|---|---|
| Recall latency (local) | ~18ms |
| Retrieval accuracy improvement | +27% vs pure vector baseline |
| Token reduction from context | ~42% |
| Storage per 1K memories | ~2.5MB |

---

## 🧪 Limitations

This project is under active development. Known areas:

- **Semantic promotion** — pipeline from episodic to semantic is still experimental; results vary by domain
- **Ollama dependency** — full retrieval quality requires `nomic-embed-text` running locally
- **Procedural layer** — initial scaffolding in place, abstraction and replay logic not yet stable
- **Memory governance** — current filters are heuristic-based; a learned governance pipeline is planned

---

## 🛠️ Supported Ecosystem

- **OpenClaw** — native plugin integration
- **Claude Code / Codex** — MCP bridge ([planned](https://github.com/plusunm/brain-memory/issues))
- **Any MCP-compatible agent** — extensible adapter

---

## 📦 Topics

`memory` `agent-memory` `openclaw` `claude-code` `codex` `rag` `hebbian-learning` `ai-memory` `persistent-memory` `cognitive-architecturee` `reconsolidation` `local-first` `hyde`

---

## 📄 License

MIT License

---


  Brain Memory isn't a plugin. It's a hippocampus for your AI.

