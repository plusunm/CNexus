# GTBS Shadow Observation (P1.5)

**Status:** operational (opt-in)  
**Constitution:** A3 (projection audit), A5 (observer separation), A6 (semantic honesty)

---

## Purpose

Measure **proposal vs reality divergence** before any GTBS enforcement decision.

Shadow mode does not:

- write to governance cycle audit (`governance_audit.jsonl`)
- influence CDG or runtime control
- trigger backpressure or retries

---

## Enable (staging)

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_staging.ps1
```

Or set environment:

```powershell
$env:BM_CONFIG = "config/staging.json"
$env:BM_MEMORY_DIR = "C:\ProgramData\brain-memory-g1\staging"
python scripts/run_ui.py
```

### Config flags (`cdg` section)

| Key | Default | Staging |
|-----|---------|---------|
| `enable_gtbs_shadow` | `false` | `true` |
| `gtbs_shadow_persist` | `false` | `true` |
| `enable_gtbs_capture` | `false` | `true` (P2 pilot) |

Production/default remains **shadow off**.

---

## Output streams

| Stream | Path | Content |
|--------|------|---------|
| Shadow observations | `{BM_MEMORY_DIR}/observability/gtbs_shadow.jsonl` | Divergence snapshots |
| Capture transactions (P2) | `{BM_MEMORY_DIR}/observability/gtbs_transactions.jsonl` | propose/approve/commit |

These are **parallel observability streams**, not replacements for CDG cycle audit.

---

## Report

```powershell
# Divergence-only quick report:
python scripts/gtbs_shadow_report.py --base-dir "C:\ProgramData\brain-memory-g1\staging"

# Full Phase A landscape report:
python scripts/phase_a_landscape_report.py --base-dir "C:\ProgramData\brain-memory-g1\staging"

# Phase B weekly longitudinal report (record snapshot + report):
python scripts/phase_b_weekly_report.py --base-dir "C:\ProgramData\brain-memory-g1\staging" --record

# Phase C monthly ecology report (record snapshot + report):
python scripts/phase_c_monthly_report.py --base-dir "C:\ProgramData\brain-memory-g1\staging" --record
```

Fields of interest:

- `proposal_reality_divergence` — 1 − Jaccard(proposed_keys, actual_key_diff)
- `structural_divergence` — count of added/removed governable keys
- `by_phase` — `interaction` vs `capture`

---

## North star

> Multi-store cognition + projection governance + emerging transaction boundary.

See [Constitutional_Semantics_v1.md](../architecture/Constitutional_Semantics_v1.md).
