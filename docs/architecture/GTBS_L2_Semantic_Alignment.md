# GTBS-L2 Semantic Alignment Layer — v0.1

**Status:** ACTIVE (read-only / instrumentation-only)  
**Version:** `0.1.0`  
**Code:** `core/governance/l2/` (canonical); `core/governance/semantic/` (compat facade)

---

## North Star

**English:**

> GTBS-L2 Semantic Alignment Layer — a read-only semantic interpretation layer that translates machine-level continuity instrumentation into human-comprehensible continuity narratives. It does not participate in runtime control, governance, mutation, or enforcement.

**中文:**

> GTBS-L2 是一个只读语义解释层，用于将机器级连续性观测翻译为人类可理解的连续性叙事。它不参与 runtime 控制、治理、mutation 或 enforcement。

---

## Purpose

Translate GTBS / Phase A / B / C machine-level instrumentation into **human-comprehensible continuity narratives**:

- proposal / approval / commit (via transaction + shadow projections)
- divergence (shadow / PRCI)
- shaping attribution
- trajectory metrics
- ecology metrics (ACD, ODC, RRE, CPI, CPX)
- singularity metrics (NCR, CEA, RSCI)

---

## L2 Semantic Alignment Principles (frozen v0.1)

| ID | Principle |
|----|-----------|
| **S1** | Read-Only Semantics — L2 never participates in runtime mutation |
| **S2** | Interpretation ≠ Governance — explains, never decides |
| **S3** | Human Alignment — prioritizes interpretability over metric completeness |
| **S4** | Divergence ≠ Failure — divergence is descriptive only |
| **S5** | Semantic Non-Actuation — output never feeds CDG / runtime / GTBS gate |

---

## Module layout

```text
core/governance/l2/
├── snapshot.py              # GTBSSnapshot multi-source aggregation
├── loader.py                # observability → snapshot
├── language.py              # classify_openness / reality / risk
├── report_templates.py      # Chinese narrative templates
├── interpreter.py           # SemanticInterpreter
└── render.py                # GTBSL2Renderer + metadata

core/governance/l2/temporal/   # v0.2 temporal window synthesis
├── types.py                   # L2TemporalWindow, L2TemporalReport
├── temporal_loader.py
├── window_builder.py
└── trajectory_synthesizer.py

core/governance/l2/fusion/     # v0.3 cross-stream fusion
├── types.py
├── fusion_loader.py
├── cross_stream_builder.py
├── semantic_coupling_engine.py
└── fusion_synthesizer.py

core/governance/l2/attractor/  # v0.5 latent attractor inference
├── types.py
├── field_to_latent.py
├── attractor_inference_engine.py
├── stability_topology.py
└── attractor_report.py

core/governance/semantic/    # backward-compatible re-exports
```

---

## v0.2 — Temporal Semantic Continuity (DONE)

**Question answered:** *how did the system become what it is* (not only *what it is now*).

Three temporal tracks:

- **Drift Narrative** — openness / NCR / basin deepening
- **Stability Narrative** — reality coupling / reconstruction bias
- **Pressure Narrative** — CPX / RSCI structural compression

Principles **S6** (No Temporal Governance) and **S7** (temporal narrative ≠ policy signal) are enforced in metadata.

---

## v0.3 — Cross-Stream Semantic Fusion (DONE)

**Question answered:** *how do shadow / ecology / singularity streams interact to form a cognitive field*.

Principles **S8** (No Cross-Stream Governance), **S9** (Coupling ≠ Causation), **S10** (Observational Closure Only).

---

## v0.5 — Latent Attractor Inference (DONE)

**Question answered:** *what latent structures are forming beneath cross-stream observations*.

Bridge: `build_attractor_field(fusion_report)` → `AttractorField` → `GTBSL2AttractorReport`.

Principles **S11** (No Control Leakage — no CDG / mutation_budget / runtime influence) and **S12** (Attractor ≠ Decision).

---

## v0.1 scope (strict)

**Does:**

```text
machine metrics → human-readable continuity narrative
```

**Does NOT:**

- runtime mutation
- governance recommendation
- auto intervention
- CDG feedback
- policy generation

---

## Usage

```powershell
python scripts/semantic_alignment_report.py --base-dir "C:\ProgramData\cnexus\staging"

# Structured JSON (snapshot + narrative sections)
python scripts/semantic_alignment_report.py --base-dir "C:\ProgramData\cnexus\staging" --json

# L2 v0.2 temporal report (default 7-day window)
python scripts/semantic_alignment_report.py --base-dir "C:\ProgramData\cnexus\staging" --temporal --window-days 7
python scripts/semantic_alignment_report.py --base-dir "..." --temporal --json

# L2 v0.3 cross-stream fusion (7-day window)
python scripts/semantic_alignment_report.py --base-dir "C:\ProgramData\cnexus\staging" --fusion --window-days 7
python scripts/semantic_alignment_report.py --base-dir "..." --fusion --json

# L2 v0.5 latent attractor inference (7-day window)
python scripts/semantic_alignment_report.py --base-dir "C:\ProgramData\cnexus\staging" --attractor --window-days 7
python scripts/semantic_alignment_report.py --base-dir "..." --attractor --json
```

Reads from observability streams only (`gtbs_shadow.jsonl`, `ecology_metrics.jsonl`, `singularity_metrics.jsonl`, etc.). Does not write back.

---

## Roadmap (not implemented)

| Version | Scope |
|---------|--------|
| **v0.1** | Single-snapshot human narrative — **DONE** |
| **v0.2** | Temporal window synthesis (drift / stability / pressure) — **DONE** |
| **v0.3** | Cross-stream semantic fusion (field cognition) — **DONE** |
| **v0.5** | Latent attractor inference (structural inference) — **DONE** |
| L3 | Attractor → governance boundary layer (not started) |
| v0.4 | Human semantic query (read-only) |

---

## Related

- [Constitutional_Semantics_v1.md](./Constitutional_Semantics_v1.md)
- [Phase_A_Divergence_Landscape.md](./Phase_A_Divergence_Landscape.md)
- [Phase_B_Longitudinal_Study.md](./Phase_B_Longitudinal_Study.md)
- [Phase_C_Ecology_Observatory.md](./Phase_C_Ecology_Observatory.md)
- [GTBS_v1.md](./GTBS_v1.md)
