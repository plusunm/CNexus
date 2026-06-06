# Brain-Memory G1

**Persistent Cognitive Runtime for Long-Lived AI Agents**  
**Stability-First AI Personality Continuity Infrastructure**

---

Brain-Memory G1 is a cognitive runtime designed to give stateless LLM agents persistent identity, long-term memory, narrative continuity, and governed personality evolution.

Unlike traditional memory systems that only store conversation history, Brain-Memory focuses on a deeper problem:

> How can an AI remain the same evolving entity across long-term interaction?

The project introduces a Stability-First architecture that combines:

* Persistent Memory Infrastructure
* Personality DNA
* Narrative Self
* Belief Governance
* Drift Detection
* Identity Anchoring
* Constitutional Safety
* Long-Term Stability Validation

Brain-Memory separates:

* reasoning → handled by foundation models
* execution → handled by agent runtimes
* continuity → handled by cognitive runtime

Its mission is not to make AI "smarter", but to make AI:

* stable
* continuous
* governable
* persistent over time

The system is designed for:

* long-lived AI agents
* personal AI companions
* autonomous runtimes
* persistent NPCs
* cognitive robotics
* multi-session AI systems

Core principle:

> Stability over uncontrolled adaptation.

Brain-Memory G1 represents a shift from:

* stateless inference  
  to  
* persistent cognitive existence.

---

## Core Architecture

```text
Foundation Model
    ↓
Agent Runtime
    ↓
Brain-Memory Cognitive Runtime
    ├── Layer 1 — Memory Infrastructure (LanceDB + Kuzu)
    ├── Layer 2 — Cognitive Runtime (router, attention, context, state)
    ├── Layer 3 — Personality Continuity (DNA, narrative, belief)
    ├── Layer 3.5 — Reflective Continuity (trait reflection → narrative + belief loop)
    ├── Layer 4 — Stability Governance (drift, anchoring, write gate)
    └── Validation & Observability
```

---

## Quick Start

### Python Runtime (recommended entry)

```bash
pip install -r requirements.txt
# or: pip install .
ollama pull nomic-embed-text   # optional; falls back to zero-vector if unavailable
```

```python
from brain_memory import create_runtime

runtime = create_runtime(project_root=".")
runtime.capture("user", "I want to build a stable long-lived AI agent", layer="goal")
print(runtime.recall("What is my long-term goal?"))
runtime.trait_based_reflection("I tend to confuse feelings with facts", ["subjectivity"])
print(runtime.run_governance_cycle())
```

CLI:

```bash
python -m brain_memory status --root .
python -m brain_memory governance --root . --json
```

### Web UI (`brain-memory-ui`)

```bash
# Terminal 1 — API (:8000)
cd brain-memory-ui
set PYTHONPATH=<project-root>          # Windows
export PYTHONPATH=<project-root>       # Linux/macOS
python -m api.main

# Terminal 2 — Frontend (:3000)
cd brain-memory-ui/frontend
npm install && npm run dev
```

Open http://localhost:3000 for dashboard, chat, memory browser, and model configuration.

> Legacy single-server UI (`python scripts/run_ui.py` on :8080) is deprecated; use `brain-memory-ui` instead.

---

## Layer 3.5 — Reflective Continuity

The reflective pipeline closes the **Subject Continuity** loop:

1. Detect traits from interaction content
2. Generate inner thought + cultivation actions
3. Persist to long-term memory and `ReflectiveMemoryStore`
4. Update **Narrative Self** and **Belief Graph**
5. Feed stability metrics back into governance

---

## Vision

Enable AI systems to maintain identity continuity, cognitive stability, consistent beliefs, coherent narrative self, and long-term relational memory — while still allowing slow, governed evolution.

---

## Keywords

Persistent Cognition • Identity Stability • Narrative Continuity • Belief Governance • Cognitive Runtime • AI Personality Infrastructure • Stability Engineering

---

## License

MIT License — see [LICENSE](LICENSE).
