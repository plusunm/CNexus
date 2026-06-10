# CNexus — Constitutional Semantics v1.0

**Status:** FROZEN  
**Product line:** CNexus — Observational Cognition Platform  
**Effective:** 2026-06-10

---

## Official positioning (frozen)

**English:**

> CNexus is a multi-store epistemic governance sidecar with advisory control, projection audit, and emerging transaction boundaries.

**中文:**

> CNexus 是一个多存储认知治理 sidecar：runtime 持有现实写权限；CDG 提供 advisory control；audit 是 projection；L7 是 post-hoc health observer；GTBS 正在逐步引入 transaction boundary。

This document is the **semantic constitution**. Executable code must not be described beyond what these axioms allow.

---

## A1 — No Canonical Σ

The system has **no unified state object**.

Cognitive state exists as parallel stores:

- Runtime objects (working self, self-model, belief, narrative)
- Unified storage (vector + memory graph)
- RealityManifold (CDG causal trace)
- CDG governable dict (snapshot projection)
- Audit / certificate projections ϕ(S)

Cross-view inconsistency is **structural**, not a bug to be patched by unification.

---

## A2 — Runtime Sovereignty

**Runtime is the sole mutation authority** for real persistence and cognitive objects.

CDG, L7, and GTBS shadow layers:

- may suggest parameters (advisory)
- may observe projections
- may produce health / divergence reports

They **do not** own final commit unless explicitly enabled in a future GTBS enforcement version (≥ v2.0).

---

## A3 — Projection Audit

Audit logs record **projections** of governance cycles, not recoverable state Σ.

Properties:

- append-only JSONL of metrics (potential_v, graph_hash, deltas, …)
- supports post-hoc analysis and certificate generation
- does **not** guarantee deterministic full-system replay

GTBS transaction events (proposal / approval / commit) when added remain **parallel streams**, not replacements for cycle audit until explicitly designed.

---

## A4 — Post-hoc Reconstruction

Transition legality, operator labels (INGEST / PRUNE / CONTROL / HOLD), and topology checks are **reconstructed from audit pairs** after execution.

There is **no complete forward transition function** F(S_t, u_t) over canonical state.

Reconstruction quality may improve (edge deltas, shadow divergence) without changing this axiom.

---

## A5 — Observer Separation

L7 (governance health report) and GTBS v1.1 shadow mode are **observers**.

Default behavior:

- observers do not enter commit path
- observers do not write audit (unless a future version explicitly adds a separate observability stream)
- observers do not trigger control backpressure

Epistemic suggestion (L7 → CDG `adjust_params`) is **parameter advisory only**, not state commit.

---

## A6 — Semantic Honesty

**External and internal language must not exceed executable semantics.**

| Do not claim | Do claim |
|--------------|----------|
| Formal Lyapunov stability / proof | Scalar descent heuristic |
| Causal proof / inferred DAG | Event trace tree + post-hoc reconstruction |
| Unified cognition / canonical state | Multi-store cognitive continuity |
| Governance enforcement (global) | Advisory governance + runtime sovereignty |
| Transaction-governed system (today) | Emerging transaction boundary (GTBS schema + shadow sensor) |
| Deterministic evolution | Projection consistency + divergence monitoring |

Heuristics must not be dressed as formal dynamics.

---

## Layer model (reference)

```text
L0  Runtime mutation (sovereign writes)
L1  Multi-store substrate
L2  Projection ϕ → metrics + audit
L3  CDG advisory control
L4  L7 post-hoc health observer
L0.5 GTBS transaction boundary (schema frozen; shadow sensor; enforcement future)
```

---

## Version cross-reference

| Artifact | Version | Status |
|----------|---------|--------|
| MSEGS axiom contract (code docstrings) | v1.0 | Active |
| GTBS schema | v1.0.0 | SCHEMA_FROZEN |
| GTBS shadow sensor | v1.1.0 | SHADOW_ONLY |
| GTBS capture pilot | v1.2.0 | CAPTURE_PILOT (opt-in) |
| Phase A landscape mapping | analytics | INSTRUMENTATION_ONLY |
| Phase B longitudinal study | singularity metrics | INSTRUMENTATION_ONLY |
| Phase C ecology observatory | ecology metrics | INSTRUMENTATION_ONLY |
| GTBS-L2 semantic alignment | read-only narratives | READ_ONLY |
| Constitutional Semantics | v1.0 | FROZEN (this document) |

---

## Non-goals (constitutional)

- Single canonical Σ
- Global transaction enforcement (pre-GTBS v2.0)
- Formal stability proofs from audit metrics
- Replacing runtime sovereignty with CDG actuation

---

## One-line product definition

> **Multi-store cognitive body + projection governance + emerging transaction boundary** — not a provably stable cognitive dynamical system.
