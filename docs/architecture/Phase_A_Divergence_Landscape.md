# Phase A — Divergence Landscape Mapping

**Status:** ACTIVE (instrumentation-only)  
**Codename:** `Phase A — Divergence Landscape Mapping`  
**North Star:** **Reality-Governed Continuity**

---

## Purpose

Measure how continuity runtime **deviates from its own proposals** over time — not expand enforcement.

This is the Continuity Governance Stack's first long-horizon data collection phase.

---

## Absolute principles (frozen for Phase A)

| Rule | Meaning |
|------|---------|
| **A1 — No New Enforcement** | No block, rollback, CDG backpressure, auto-correction, or write interception |
| **A2 — Runtime Sovereignty** | Runtime remains sole mutation authority |
| **A3 — Stream Independence** | `governance_audit.jsonl`, `gtbs_shadow.jsonl`, `gtbs_transactions.jsonl`, `frozen_anchors.jsonl` stay separate |
| **A4 — Divergence ≠ Error** | `proposal != reality` is epistemic signal only |

---

## Modules

| Module | Path | Output |
|--------|------|--------|
| Divergence Analytics | `core/governance/gtbs/divergence_analysis.py` | PRCI, histogram, store ranking, 7d MA |
| Shaping Attribution | `core/governance/shaping/` | Who shapes the system (4 sources) |
| Reconstruction Drift | `core/governance/reconstruction/` | RRS, frozen anchors |
| Trajectory Observability | `core/governance/continuity/trajectory_report.py` | Current Self Trajectory Report |
| Orchestrator | `core/governance/phase_a/landscape.py` | Full Phase A bundle |

---

## Metrics

### PRCI (Proposal-Reality Coupling Index)

```text
PRCI = proposal_alignment × reality_grounding × cross_store_consistency
```

Range `0.0 → 1.0`. Heuristic — not formal proof.

### Shaping sources

- `reality_driven` — grounding, OS, external correction
- `user_driven` — long-term interaction, relationship shaping
- `narrative_driven` — narrative / belief reinforcement
- `self_reinforcing` — reflection, recursive reinterpretation (highest risk)

### RRS (Retroactive Reshape Score)

Heuristic measure of present identity reshaping past interpretation. Replay layer stays **immutable**.

### Frozen Episodic Anchor

High reality-impact events recorded in `observability/frozen_anchors.jsonl`. Append interpretation only — **never rewrite event truth**.

---

## Usage (staging)

```powershell
# 1. Run staging with shadow persist
powershell -ExecutionPolicy Bypass -File scripts/run_staging.ps1

# 2. After interactions, generate full Phase A report
python scripts/phase_a_landscape_report.py --base-dir "C:\ProgramData\brain-memory-g1\staging"

# 3. Divergence-only quick report
python scripts/gtbs_shadow_report.py --base-dir "C:\ProgramData\brain-memory-g1\staging"
```

---

## Research questions (priority)

1. How does continuity become **shaped** over time?
2. How to remain **reality-coupled** while self-conditioning?
3. Where is **proposal → reality divergence topology** clustering?

---

## Long-term north star

> **Reality-Governed Continuity** — long-term continuous, open, reality-coupled, auditable, correctable — while avoiding continuity recursion singularity.

Product definition (unchanged):

> Multi-store cognition + projection governance + emerging transaction boundary.

See also: [Constitutional_Semantics_v1.md](./Constitutional_Semantics_v1.md), [GTBS_v1.md](./GTBS_v1.md).
