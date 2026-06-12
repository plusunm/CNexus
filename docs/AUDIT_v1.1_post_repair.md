# CNexus Audit v1.1 — Post Repair Baseline

**Commit anchor:** `44e3f00` and subsequent P3-A work  
**Audit method:** Raw fetch + line-by-line review (`brain_memory/runtime.py`, `memory/runtime_guard.py`)  
**Date:** 2026-06-12

---

## Executive Summary

CNexus has entered a **verifiable Kernel prototype** phase. Hot-path guard, L1 block recall, GovernancePipeline, and 360+ automated tests are **real in code**, not documentation-only. The system is **not production-ready** for public 7×24 deployment without P3-A/B/C gates.

---

## Locked Scores (post `44e3f00`)

| Lens | Score |
|------|-------|
| **Kernel repair (P0–P2)** | **88/100** |
| **Production readiness** | **42/100** → target 70+ after P3-B |
| **Reality First composite** | **50/100** |
| **Vision gap** | **65%** |

Prior scores of **35/100** underestimated Kernel repair; **96/100** overestimated production readiness.

---

## Verified Code Facts

### `memory/runtime_guard.py` (L30–60)

- `runtime_write_context` increments `_runtime_write_depth`
- `assert_runtime_context(operation)` raises `RuntimeViolationError` when depth == 0
- Bypass only via `CNEXUS_BYPASS_RUNTIME_GUARD=1` (must be blocked in production)

### `brain_memory/runtime.py` (L80–200+)

- `MemoryManager(..., write_gate=self.policy.write_gate)`
- `belief_engine.restore_from_memory_manager()` on startup
- `GovernancePipeline(deliberation, cdg, values_governance, intent_engine)`
- `RecallPipeline` single recall facade
- Legacy `/api/chat`, `/ws/chat` routed through `process_interaction`
- Belief/Narrative block dual-write + restart recovery

---

## Precision Boundaries

| Topic | Boundary |
|-------|----------|
| **Write entry** | `MemoryManager` direct writes blocked; `runtime.capture()` / `process_interaction()` / `trait_based_reflection()` remain legal Runtime-layer entries |
| **Full cognitive loop** | `POST /v1/capture`, scripts may call `capture()` without CDG/deliberation/reflection chain |
| **Governance order** | Pre-output: Deliberation via `GovernancePipeline`; Post-mutation: CDG; Values default **OBSERVE** (configurable in P3-A) |
| **Tests** | 360 passed cover guard/blocks/E2E/security; Attention/Reflection **benchmarks** added in P3-A |

---

## Dimension Scores

| Dimension | Score | Notes |
|-----------|-------|-------|
| Architecture | 6.5/10 | Hot path ≈ architecture diagram |
| Runtime | 6.5/10 | Guard + RecallPipeline + entry registry (P3-A) |
| Memory | 6/10 | L1 blocks + belief/narrative persist; full schema unification pending |
| Governance | 4/10 → 5/10 | Pipeline exists; Values enforcement configurable P3-A |
| Product | 5/10 | v1 REST + OpenAI + WS |
| Enterprise | 2/10 | No JWT/multi-tenant |

---

## Top Risks (remaining)

1. Attention effectiveness unproven without benchmark CI gate  
2. Reflection behavioral loop weak  
3. CDG runs after irreversible state mutations  
4. `/v1/capture` partial loop  
5. No auth/rate-limit on API  
6. JSON block store non-atomic writes  
7. Kuzu silent in-memory fallback  
8. Multi-tenant isolation absent  
9. Lance metadata / user_id not in vector rows  
10. Long-run chaos / 72h tests absent  

---

## Top Strengths

1. `runtime_write_context` strict guard  
2. `GovernancePipeline` + CDG wiring  
3. Belief/Narrative block dual-write + restore  
4. 360+ tests + P3-A benchmark suite  
5. v1 REST + OpenAI compatible + shared WS  
6. Legacy chat → `process_interaction`  
7. `scripts/check_write_paths.py` CI gate  
8. `RecallPipeline` unified recall  
9. ReflectiveMemoryStore partial loop  
10. Active P0–P2 delivery on `main`  

---

## Reality First — Next Priority (P3-A)

1. Benchmark suite (memory / attention / reflection on-off)  
2. `migrate_narrative.py` + Values FLAG/REWRITE/BLOCK modes  
3. Lance roundtrip integration test + `test_attention_changes_prompt_diff`  
4. Observability metrics + structured trace IDs  
5. Chaos governance + injection hardening loop  

---

## Production Gates (summary)

See [PRODUCTION_READINESS_MATRIX.md](./PRODUCTION_READINESS_MATRIX.md) for the full matrix.

**Minimum pilot production:** Gate A (security) + Gate B (storage durability) + Gate D (benchmark baseline).

---

## Conclusion

CNexus is a **verifiable Kernel prototype**, not a production cognitive OS. The path to **70–80 production readiness** requires **measurability + reliability + security + operability** — not new L7/L8 cognitive modules.
