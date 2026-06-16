# Execution Tiering v1 — Delivery Package

**Status:** Shipped (convergence stopped)  
**Scope:** Kernel Performance Split — tier routing, fast path, async observability, lazy record  
**Date:** 2026-06-14

---

## Summary

CNexus execution no longer forces every chat through full DAG + sync observability + inline record materialization.

```
INTENT → resolve_execution_tier() → T0 | T1 | T2 | T3 → ExecutionRecord
```

Single Truth Kernel preserved. T0/T1 use lazy records; enforce gate allows `graph=None` for light tiers.

---

## Tier Matrix

| Tier | Trigger | Graph | Recall | Spine (sync path) | Record |
|------|---------|-------|--------|-------------------|--------|
| T0 | `payload.fast=true` | None | Once (prefetch) | Skipped | Lazy |
| T1 | `use_memory=false` | None | None | Skipped | Lazy |
| T2 | Default chat | Single node | Once (in chat) | Async queue | Full |
| T3 | `deep_reasoning=true` or non-chat | recall→chat DAG | Once (prefetch) | Async queue | Full |

---

## API / Payload

```json
{ "message": "hello", "fast": true }
{ "message": "hello", "use_memory": false }
{ "message": "hello" }
{ "message": "hello", "deep_reasoning": true }
```

Record fields: `derivation.execution_tier`, `audit.execution_tier`.

---

## Environment

| Variable | Default | Effect |
|----------|---------|--------|
| `KERNEL_TAP_SYNC` | off | `1` = sync tap/spine (tests/debug) |
| `USE_EXECUTION_GRAPH` | `1` | `0` = route_intent only (T2/T3 graph branch skipped) |
| `USE_EXECUTION_KERNEL` | `1` | Kernel off when `0` (enforce may block) |

---

## Files (this package)

### New

- `core/kernel/tier/__init__.py`
- `core/kernel/tier/resolver.py`
- `core/kernel/tier/fast_path.py`
- `core/kernel/tier/minimal_path.py`
- `tests/test_kernel_execution_tier.py`
- `packaging/EXECUTION_TIERING_V1.md`

### Modified

- `core/kernel/kernel.py` — tier dispatch entry
- `core/kernel/hooks.py` — async tap/spine queues
- `core/kernel/record.py` — `LazyExecutionRecord`, `materialize_lazy`
- `core/kernel/context.py` — `meta` bag
- `core/kernel/graph/builder.py` — tier-aware graph shape
- `core/kernel/enforce/gate.py` — T0/T1 graph exemption
- `brain_memory/runtime.py` — `recall_prefetch` consumption
- `tests/test_execution_graph_kernel.py`
- `tests/test_execution_kernel.py`
- `tests/test_api_bypass_kill.py`
- `tests/test_kernel_final_verification.py`
- `tests/test_kernel_enforce.py`
- `tests/test_replay_engine_v1.py`

---

## Verification

```powershell
Set-Location "<repo-root>"
python -m pytest tests/test_kernel_execution_tier.py tests/test_execution_graph_kernel.py tests/test_execution_kernel.py tests/test_kernel_enforce.py tests/test_kernel_final_verification.py tests/test_api_bypass_kill.py tests/test_replay_engine_v1.py -q
```

Expected: all pass.

---

## Explicitly NOT in this package

- WS default T0 routing
- Explain stream tail-follow / poll fix
- Kernel OS Scheduler v2 (priority / cost-aware)
- UI tier indicators

---

## Architecture note

Kernel remains sole truth. Tiering changes **when** graph/identity/projections run, not **whether** execution is kernel-governed.
