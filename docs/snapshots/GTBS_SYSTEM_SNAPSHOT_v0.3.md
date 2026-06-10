# GTBS / G1 System Snapshot — v0.3 (L2.5 Complete)

**Snapshot Version:** `GTBS / G1 L2.5 COMPLETE`  
**Tag:** `gtbs-snapshot-v0.3-l2.5`  
**Date:** 2026-06-10  
**State:** Observational → Structural Inference Phase  
**Governance Status:** NONE (instrumentation-only for L2 / L2.5 stack)

---

## 1. System phase definition

This snapshot freezes Brain-Memory G1 at the completion of the GTBS observability + L2 semantic cognition stack through **L2.5 Latent Attractor Inference**.

| Layer | Version | Question answered |
|-------|---------|-------------------|
| L2 v0.1 | Snapshot Semantics | What exists now? |
| L2 v0.2 | Temporal Semantics | How did it change over time? |
| L2 v0.3 | Fusion Semantics | How do streams interact to form a cognitive field? |
| L2.5 | Attractor Inference | What latent structures form beneath observations? |

**Not included in this freeze:** L3 governance boundary layer (attractor → policy isolation). That layer is explicitly deferred.

---

## 2. System capability boundary

This snapshot represents a **purely observational cognition system**.

| Boundary | Status |
|----------|--------|
| No control authority | ✅ L2 / L2.5 never actuate |
| No runtime mutation influence | ✅ Read-only over observability streams |
| No CDG feedback loop | ✅ Semantic output does not feed CDG |
| No enforcement layer | ✅ GTBS v1.x schema + instrumentation only |
| Pure observational cognition stack | ✅ Interpretation layers only |

**Constitutional principles frozen in this snapshot:**

- **A1–A6** (Constitutional Semantics v1.0): read-only semantics, divergence ≠ error
- **S1–S5** (L2 v0.1): semantic non-actuation
- **S6–S7** (L2 v0.2): no temporal governance
- **S8–S10** (L2 v0.3): no cross-stream governance; coupling ≠ causation
- **S11–S12** (L2.5): no control leakage; attractor ≠ decision

---

## 3. Cognitive architecture (text diagram)

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    GOVERNANCE ISOLATION BOUNDARY                         │
│  (L2 / L2.5 MUST NOT cross this line — no CDG / runtime / GTBS gate)   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ read-only narrative outputs
                                    │
┌───────────────────────────────────┴───────────────────────────────────────┐
│                         L2.5 ATTRACTOR INFERENCE LAYER                     │
│  core/governance/l2/attractor/                                            │
│  fusion_report → LatentAttractorState → AttractorField → GTBSL2AttractorReport │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴───────────────────────────────────────┐
│                         L2 v0.3 FUSION LAYER                               │
│  core/governance/l2/fusion/                                               │
│  shadow × ecology × singularity → CrossStreamField → fusion narratives    │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴───────────────────────────────────────┐
│                         L2 v0.2 TEMPORAL LAYER                             │
│  core/governance/l2/temporal/                                             │
│  time-window snapshots → drift / stability / pressure narratives          │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴───────────────────────────────────────┐
│                         L2 v0.1 SNAPSHOT LAYER                             │
│  core/governance/l2/ (snapshot, loader, interpreter, render)              │
│  observability → GTBSSnapshot → human continuity narrative                │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │
┌───────────────────────────────────┴───────────────────────────────────────┐
│                      OBSERVABILITY STREAMS (append-only)                   │
│  observability/gtbs_shadow.jsonl          — divergence / proposal-reality │
│  observability/ecology_metrics.jsonl      — ACD / ODC / RRE / CPI / CPX   │
│  observability/singularity_metrics.jsonl — NCR / CEA / RSCI              │
│  observability/gtbs_transactions.jsonl    — propose / approve / commit    │
│  observability/frozen_anchors.jsonl       — frozen reconstruction anchors │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ instrumentation hooks (P1.5 / P2 pilot)
                                    │
┌───────────────────────────────────┴───────────────────────────────────────┐
│                    RUNTIME / CDG / GTBS (NOT IN L2 SCOPE)                  │
│  Runtime = sole mutation authority                                        │
│  CDG = advisory (non-sovereign)                                           │
│  GTBS v1.0 = schema freeze + capture boundary pilot                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data flow

### Primary semantic pipeline

```text
shadow stream        → L2 snapshot / fusion coupling
ecology stream       → L2 snapshot / temporal / fusion coupling
singularity stream   → L2 snapshot / fusion / pressure field
continuity metrics   → temporal trajectory / fusion reconstruction bias

L2 v0.1 snapshot  ──┐
L2 v0.2 temporal  ──┼──→ L2 v0.3 fusion ──→ L2.5 attractor inference
Phase A/B/C       ──┘

all outputs → read-only narrative (CLI / JSON report)
```

### Stream-specific paths

| Stream | Phase module | L2 consumption |
|--------|--------------|----------------|
| `gtbs_shadow.jsonl` | Phase A + GTBS P1.5 | divergence, alignment, cross-store |
| `ecology_metrics.jsonl` | Phase C | ACD, ODC, RRE, CPI, CPX |
| `singularity_metrics.jsonl` | Phase B | NCR, CEA, RSCI |
| `gtbs_transactions.jsonl` | GTBS P2 | transaction boundary context |
| `frozen_anchors.jsonl` | Reconstruction | RRS / frozen anchor context |

### CLI entry points

```powershell
python scripts/semantic_alignment_report.py --base-dir <BM_MEMORY_DIR>                    # L2 v0.1
python scripts/semantic_alignment_report.py --base-dir <BM_MEMORY_DIR> --temporal         # L2 v0.2
python scripts/semantic_alignment_report.py --base-dir <BM_MEMORY_DIR> --fusion           # L2 v0.3
python scripts/semantic_alignment_report.py --base-dir <BM_MEMORY_DIR> --attractor        # L2.5
python scripts/phase_a_landscape_report.py --base-dir <BM_MEMORY_DIR>
python scripts/phase_b_weekly_report.py --base-dir <BM_MEMORY_DIR>
python scripts/phase_c_monthly_report.py --base-dir <BM_MEMORY_DIR>
```

---

## 5. Backup scope (module inventory)

### Core governance modules (frozen)

```text
core/governance/gtbs/           — GTBS v1.0 schema, divergence, capture boundary
core/governance/semantic/       — compat facade → l2/
core/governance/l2/             — L2 v0.1–v0.3 + L2.5 attractor
core/governance/ecology/          — Phase C observatory
core/governance/singularity/    — Phase B longitudinal study
core/governance/shaping/        — shaping attribution
core/governance/continuity/     — trajectory report
core/governance/phase_a/        — divergence landscape
core/governance/reconstruction/ — RRS + frozen anchors
```

### L2 canonical layout

```text
core/governance/l2/
├── snapshot.py, loader.py, interpreter.py, render.py, language.py
├── temporal/                   # v0.2
├── fusion/                     # v0.3
└── attractor/                  # v0.5 (L2.5)
```

### Observability paths (structure only — no data bundled)

| Path | Format | Key fields |
|------|--------|------------|
| `observability/gtbs_shadow.jsonl` | JSONL | `timestamp`, `proposal_vs_reality.*` |
| `observability/ecology_metrics.jsonl` | JSONL | `ts`, `acd`, `odc`, `rre`, `cpx`, `cpi` |
| `observability/singularity_metrics.jsonl` | JSONL | `ts`, `ncr`, `cea`, `rsci` |
| `observability/gtbs_transactions.jsonl` | JSONL | GTBS transaction events (P2 pilot) |
| `observability/frozen_anchors.jsonl` | JSONL | frozen reconstruction anchors |

Data content is **not** included in this repository snapshot. Only schema references and format documentation in `docs/architecture/` and `docs/operations/`.

---

## 6. Risk boundary (critical)

| Risk | Mitigation in this snapshot |
|------|----------------------------|
| Control leakage | S11: L2.5 metadata `no_control_leakage=true` |
| Policy generation | L2 explicitly does not generate policy |
| Mutation authority | Runtime remains sole mutation authority |
| Runtime coupling | L2 outputs never feed CDG / GTBS gate / write paths |
| Causal over-claim | S9: coupling ≠ causation in all fusion narratives |
| Attractor → action | S12: attractor field = structure description only |

**Do NOT** wire L2 / L2.5 outputs into:

- CDG gradient controller
- GTBS gatekeeper enforcement
- Runtime capture / mutation paths
- mutation_budget or write_gate

---

## 7. Reproducibility

```powershell
cd <repo-root>
python -m unittest discover -s tests -v
# Expected: 121+ tests OK (includes test_gtbs_l2_*, test_phase_*)
```

Staging launcher: `scripts/run_staging.ps1`  
Staging config: `config/staging.json`

---

## 8. Related documentation (frozen)

- [GTBS_L2_Semantic_Alignment.md](../architecture/GTBS_L2_Semantic_Alignment.md)
- [Constitutional_Semantics_v1.md](../architecture/Constitutional_Semantics_v1.md)
- [GTBS_v1.md](../architecture/GTBS_v1.md)
- [Phase_A_Divergence_Landscape.md](../architecture/Phase_A_Divergence_Landscape.md)
- [Phase_B_Longitudinal_Study.md](../architecture/Phase_B_Longitudinal_Study.md)
- [Phase_C_Ecology_Observatory.md](../architecture/Phase_C_Ecology_Observatory.md)
- [GTBS_Shadow_Observation.md](../operations/GTBS_Shadow_Observation.md)
- [ARCHITECTURE_GRAPHS.md](./ARCHITECTURE_GRAPHS.md)
- [SYSTEM_INDEX.json](./SYSTEM_INDEX.json)

---

## 9. Next phase (NOT in this snapshot)

**L3 — Attractor → Governance Boundary Layer**

Deferred. Will define policy isolation architecture and runtime mutation safety fence. Must not be implemented without explicit constitutional review.
