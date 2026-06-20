# CNexus v1.0.0-stable — Release Notes

**Tag target:** `v1.0.0-stable`  
**Branch:** `main` @ `b1f2fdc` (CNexus remote)  
**Date:** 2026-06-20 UTC

CNexus is a layered cognitive runtime with observational governance, domain-split SelfModel persistence, and conscious-flow simulation. This release marks the convergence of **L1–L4 architecture** with **product-grade License/Security/UI** integration.

---

## Architecture Milestones

| Layer | Capability | Key modules |
|-------|------------|-------------|
| **L1–L2** | Domain storage (Σ.S/Σ.I/Σ.M), Σ.T sharding, canonical trace IDs | `domain_storage`, `trace_store` |
| **L3-1** | Short-term narrative (`recent_narrative`) | `recent_context`, `recall_pipeline` |
| **L3-2** | Attractor stability loop (Σ.S heal) | `stability_monitor`, `TrajectoryEvaluator` |
| **L3-3** | Daily belief consolidation (Σ.I async) | `daily_consolidation`, `apply_consolidation_step` |
| **L4-1** | Parallel thought branching (Σ.T sandbox) | `SimulationEngine`, `SimulationBudget` |
| **L4-2** | Cognitive trajectory filter / prune | `TrajectoryEvaluator`, `eval_step` |
| **L4-3** | Reasoning trace + stream phases | `ReasoningTrace`, `ChunkedResponse` |
| **Product** | License guard, security harness, Tauri desktop | `license_guard`, `security_harness` |

---

## Performance & Compliance Promises (FULL BOOT)

Verified by `scripts/layer2_full_boot_verify.py` — **run `181a6d08a08f`** (post License integration):

| Gate | Promise | Result |
|------|---------|--------|
| **B1** | API `operational_ready` within 120s | ✅ PASS (~45s wall) |
| **B2** | AST observability compliance — 0 leaks | ✅ PASS |
| **B3** | Governance stability readable | ✅ `overall_stability_score ≈ 0.956` |
| **B4** | Cross-shard Σ.T observe | ✅ PASS |
| **B5** | `/v1/interact` smoke (mock LLM) | ✅ PASS — License middleware non-blocking |
| **B6** | Canonical `t-{16hex}` trace IDs | ✅ PASS |
| **B7** | Chat path: **cognize-only** mtime update | ✅ `self_model_decide.json` unchanged |
| **B8** | `interaction_step` in Σ.T | ✅ PASS |
| **L4-1** | `simulation_step` sandbox traces | ✅ PASS |
| **L4-2** | Dangerous branches pruned | ✅ PASS |
| **L4-3** | Reasoning trace + Σ.I isolation | ✅ PASS |
| **B9** | Automated summary | ✅ **Overall PASS** |

Full report: [`docs/migration/LAYER2_FULL_BOOT_REPORT.md`](docs/migration/LAYER2_FULL_BOOT_REPORT.md)

---

## Boundary Guarantees

1. **Fast Lane:** L0 chat uses `apply_cognize_step()` only — no synchronous `integrate()` on chat path.
2. **Σ.I writes:** Core beliefs / autobiography updates via L3-3 `daily_consolidation` async loop only.
3. **Σ.S writes:** Attractor recalibration capped at `|Δcoherence| ≤ 0.1`.
4. **L4 sandbox:** All simulation/eval traces in Σ.T — unverified branches never persist to decide domain.
5. **License/Security:** Input audit at API middleware — does not block Σ.T read or `recent_narrative` extraction.

---

## Automated Test Matrix (release gate)

| Suite | Count | Status |
|-------|-------|--------|
| Security + License | 15 | ✅ PASS |
| L4 conscious flow | 19 | ✅ PASS |
| L3 reflection / attractor | 26+ | ✅ PASS |
| FULL BOOT B1–B9 + L4 | 12 gates | ✅ PASS |

---

## Manual Sign-off Remaining

| Item | Owner | Status |
|------|-------|--------|
| **B10** Tauri desktop snapshot smoke | Human reviewer | ☐ Pending |
| Production `CNEXUS_REASONING_TRACE` policy | Ops | Default off in production |

---

## Quick Start

```bash
# FULL BOOT verification
python scripts/layer2_full_boot_verify.py

# Layer 4 unit suite
python -m pytest tests/test_conscious_flow_simulation.py tests/test_trajectory_evaluator.py tests/test_reasoning_trace_l4.py -q

# Security harness
python -m pytest tests/security/ -q
```

---

## Upgrade Notes

- `CaptureMode` is now **required explicitly** on chat capture paths; legacy callers default to `INGEST`.
- Enable reasoning trace in dev: `CNEXUS_REASONING_TRACE=1`
- Production license endpoints: `/v1/system/license_status`, `/v1/session/heartbeat`
