# GTBS v1.0 — Governance Transaction Boundary Spec (Schema Freeze)

**Status:** `SCHEMA_FROZEN`  
**Version:** `1.0.0`  
**Code anchor:** `core/governance/gtbs/types.py`  
**Related:** MSEGS axiom contract (CDG / L7 / audit projection layer)

---

## 1. Purpose

This spec defines the **proposal → approval → commit** boundary for all state mutations in Brain-Memory G1.

GTBS v1.0 is **schema-only**. It does not intercept writes, does not modify CDG, and does not change runtime behavior.

---

## 2. Current system context (reconciliation)

| Layer | Name | Status on disk |
|-------|------|----------------|
| L0 | Runtime mutation (sovereign writes) | Exists — multiple write paths |
| L1 | Multi-store substrate (Reality / Cognitive / Storage / Personality) | Exists — no canonical Σ |
| L2 | Projection ϕ(S) → metrics + audit | Exists — MSEGS v1.0 |
| L3 | CDG advisory (dict projection + param suggestions) | Exists — non-sovereign |
| L4 | L7 observation (health report) | Exists — observer-only |
| **L0.5** | **GTBS transaction boundary** | **This spec — types only (P0)** |

**Fact:** CDG ≠ transaction authority. Runtime remains mutation authority until GTBS enforcement (v2.0).

---

## 3. MSEGS axiom mapping

| Axiom | GTBS v1.0 stance |
|-------|------------------|
| A1 — No canonical Σ | Proposals declare `target_store` per delta; no unified state object |
| A2 — Advisory control | CDG output lives in `cdg_decision`; not commit authority |
| A3 — Projection-only audit | GTBS audit events parallel cycle JSONL; do not replace ϕ(S) rows |
| A4 — Post-hoc reconstruction | Operation labels describe intent; no forward model F(S,u) |
| A5 — L7 observer-only | L7 may appear in `justification.source`, never in commit path (v1.0) |

---

## 4. Core types

Defined in `core/governance/gtbs/types.py`:

- `StateDelta` — single-store mutation description
- `GovernanceProposal` — proposed change set + justification
- `GovernanceTransaction` — state-machine carrier
- `AuditTransactionEvent` — parallel audit stream event
- Enums: `TransactionState`, `OperationType`, `JustificationSource`

---

## 5. Transaction state machine

```text
PROPOSED ──→ APPROVED ──→ COMMITTED
    │            │
    ├── REJECTED │
    └── DEFERRED ┘
```

Rules (v1.0 spec):

- Only `APPROVED` may transition to `COMMITTED` (enforcement deferred to v1.1+).
- `COMMITTED` requires runtime authority (not CDG).
- State transitions are recorded via `GovernanceTransaction.transition_to()`.

---

## 6. Commit boundary (defined, not enforced)

v1.0 defines but does **not** enforce:

```text
ALL writes → (future) RuntimeGatekeeper.commit() → single sink
```

Current runtime write paths (`capture`, `integrate`, `update_from_input`, etc.) remain unchanged.

---

## 7. Audit requirements

GTBS events use explicit `event_type`:

- `proposal`
- `approval`
- `commit`
- `rejection`
- `defer`

These are **parallel** to existing `governance_audit.jsonl` cycle records (`potential_v`, `graph_hash`, …).  
Do not merge streams until v1.1 shadow mode design is approved.

Each GTBS event includes `gtbs_version` for contract traceability.

---

## 8. Version roadmap

| Version | Mode | Scope |
|---------|------|-------|
| **v1.0** | Schema Freeze | Types + this doc only (P0) — **DONE** |
| **v1.1** | Shadow Mode | `RuntimeGatekeeper.observe_runtime_event()` — divergence sensor only — **DONE** |
| **v1.2** | Partial Gate | `capture()` propose-commit pilot — **DONE (opt-in via `enable_gtbs_capture`)** |
| v2.0 | Enforcement | All writes through GTBS commit |

**Rule:** v1.0 schema is immutable except v1.0.x patch (doc typos, non-breaking field defaults).  
Breaking changes require GTBS v2.0.

---

## 9. GTBS v1.1 Shadow Mode (P1 — divergence sensor)

**Code:** `core/governance/gtbs/gatekeeper.py`  
**Version:** `1.1.0` / `SHADOW_ONLY`

P1 is **not** governance, gate, or transaction enforcement. It is a **Pure Epistemic Divergence Sensor**:

```text
observe(proposal/context, pre_state, post_state) → Δ divergence report (non-actionable)
```

### P1 invariants (frozen)

1. **Epistemic Inertia** — observation cannot alter evolution path  
2. **No-Backpressure** — divergence cannot trigger mutation / adjust / reject / retry  
3. **Non-Coherence** — mismatch ≠ error ≠ alert ≠ control signal  

### Explicitly forbidden in v1.1

- Block mutation  
- Influence CDG or runtime policy  
- Audit write-back  
- Alerting or feedback loops  

Runtime wiring is **optional** and must only attach the observation dict to response metadata when enabled; default off preserves existing behavior.

### P1.5 observability (shadow persist)

When `cdg.gtbs_shadow_persist: true`, observations append to:

`{BM_MEMORY_DIR}/observability/gtbs_shadow.jsonl`

See `docs/operations/GTBS_Shadow_Observation.md`.

---

## 9b. GTBS v1.2 Capture Pilot (P2 — partial gate)

**Code:** `core/governance/gtbs/capture_boundary.py`  
**Version:** `1.2.0` / `CAPTURE_PILOT`

Opt-in via `cdg.enable_gtbs_capture: true` (staging config). Only `capture()` uses propose → approve → commit; all other write paths unchanged.

Transaction events append to `observability/gtbs_transactions.jsonl` (parallel stream, not cycle audit).

---

## 10. Non-goals (v1.0–v1.2)

- No global write interception (v2.0 only)
- No CDG refactor into commit authority
- No claim of dynamical-system or formal-proof status
- No Lyapunov / L7 formula changes for “proof” narrative

---

## 11. One-line system identity (target, post-enforcement)

> A multi-store epistemic system where all state mutations are explicit governance transactions mediated by runtime authority, with CDG as advisory risk evaluator and L7 as projection-only observer.

**Current (pre-GTBS enforcement):** MSEGS v1.0 with advisory CDG and multi-port runtime mutation.

See also: [Constitutional_Semantics_v1.md](./Constitutional_Semantics_v1.md) (frozen positioning + A1–A6).
