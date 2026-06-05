<div align="center">
  <h1>🧠 Brain Memory v5.0</h1>
  <p><strong>Cognitive Stability Architecture for AI agents — local-first, deterministic, evolvable.</strong></p>
  <p>Deterministic Router · Belief System · Reflection Engine · Goal Lifecycle · HyDE · Hebbian</p>
  <p>
    <a href="https://github.com/plusunm/brain-memory/stargazers"><img src="https://img.shields.io/github/stars/plusunm/brain-memory?style=flat-square" alt="Stars"></a>
    <a href="LICENSE"><img src="https://img.shields.io/github/license/plusunm/brain-memory?style=flat-square" alt="License"></a>
    <img src="https://img.shields.io/badge/version-5.0.0-blue?style=flat-square" alt="Version">
    <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square" alt="Python">
    <img src="https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20macos-lightgrey?style=flat-square" alt="Platform">
  </p>
</div>

---

## Your AI stops forgetting.

**Stop re-explaining your project to AI every day.**

Brain Memory gives your agents persistent long-term memory across sessions. v5.0 adds **Cognitive Stability**: deterministic routing, belief reconciliation, meta-reflection, and goal lifecycle tracking — so memory evolves without drifting out of control.

```bash
openclaw plugins install brain-memory
openclaw config set plugins.slots.memory brain-memory
```

Or clone this repo into your OpenClaw extensions directory:

```bash
git clone https://github.com/plusunm/brain-memory.git
cd brain-memory
pip install -r requirements.txt
```

---

## v5.0 Highlights

| Module | Description |
|--------|-------------|
| **DeterministicRouter** | Keywords → embedding prototypes → LLM fallback (stable routing) |
| **Dynamic Attention Field** | Working memory with half-life decay (`attention_half_life`) |
| **Belief System** | `beliefs.json` + compatibility check on write |
| **Reflection Engine** | `run_reflection()` → `meta` layer + identity stability score |
| **Goal Lifecycle** | `goal_lifecycle.json` + status tracking (active/completed/…) |
| **Cognitive Governance** | Write gate + belief conflict gate + metabolic reconciliation |

Inherited from v4.x: HyDE recall, multi-hop Kuzu graph, schema layers, provenance, sleep consolidation, Ebbinghaus forgetting.

---

## Quick Start

### Requirements

- Python 3.11+
- Ollama (`nomic-embed-text`, `llama3.2` or similar)

### Install (Windows)

```powershell
cd extensions\brain-memory
scripts\install.bat
pip install -r requirements.txt
ollama pull nomic-embed-text
ollama pull llama3.2:3b
```

### OpenClaw config

```json
{
  "plugins": {
    "slots": { "memory": "brain-memory" },
    "entries": {
      "brain-memory": {
        "enabled": true,
        "config": {
          "use_hyde": true,
          "enable_metabolic": true,
          "write_gate_threshold": 0.45,
          "attention_half_life": 3600,
          "reflection_enabled": true
        }
      }
    }
  }
}
```

### Verify

```python
from memory_backend import BrainMemoryBackend
b = BrainMemoryBackend()
print(b.get_stats())
print(b.recall_detail("我的核心目标是什么"))
```

---

## Architecture

```
User Input
    ↓
DeterministicRouter (goal / semantic / reflect / episodic / …)
    ↓
├── Attention Working Memory (half-life decay)
├── LanceDB (HyDE + vector)
├── Kuzu Graph (Hebbian + multi-hop)
├── Belief System + Self-Model
└── Nightly: Consolidation + Reflection + Metabolic cycle
```

---

## Agent Tools

| Tool | Description |
|------|-------------|
| `brain_recall` | Hybrid recall with deterministic routing |
| `brain_recall_detail` | Full context + route + provenance |
| `brain_reflect` | Meta-memory reflection |
| `brain_update_goal` | Goal lifecycle write |
| `brain_store` | Capture with write gate + belief check |
| `brain_consolidate` | Sleep consolidation + metabolic cycle |
| `brain_stats` | Health + belief_count + stability_score |

See `brain_skill/SKILL.md` for the full tool list.

---

## Feature Comparison

| Feature | Brain Memory v5 | mem0 | Vector DB Only |
|---------|-----------------|------|----------------|
| Deterministic routing | ✅ | ❌ | ❌ |
| Belief + reflection | ✅ | ❌ | ❌ |
| Hebbian graph | ✅ | ❌ | ❌ |
| Reconsolidation | ✅ | ❌ | ❌ |
| HyDE retrieval | ✅ | ⚠️ | ❌ |
| Multi-layer memory | ✅ | ⚠️ | ❌ |
| Local-first | ✅ | ⚠️ | ✅ |
| OpenClaw native | ✅ | ⚠️ | ❌ |

---

## Runtime Data

The `memory/` directory is created at runtime (LanceDB, Kuzu, beliefs, etc.) and is **gitignored**. Existing LanceDB tables (`brain_chat_memory`) migrate forward across versions.

---

## License

MIT — see [LICENSE](LICENSE).

<p align="center"><strong>Brain Memory isn't a plugin. It's a hippocampus for your AI.</strong></p>
