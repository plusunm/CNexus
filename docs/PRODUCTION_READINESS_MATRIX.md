# CNexus Production Readiness Matrix

**Baseline:** Audit v1.1 post `44e3f00`  
**Target tiers:** Pilot (70–80) · Enterprise pilot (80–90) · Platform (90+)

---

## Score Targets (when complete)

| Lens | Current | Pilot | Enterprise | Platform |
|------|---------|-------|------------|----------|
| Kernel repair | 88 | 92 | 94 | 95 |
| Production readiness | 42 | 70–80 | 80–90 | 90+ |
| Composite maturity | 50 | 72 | 82 | 88+ |

---

## 12 Dimensions

### 1. Runtime Kernel

| Item | Priority | Status |
|------|----------|--------|
| RuntimeWriteGuard | P0 | Done |
| Entry capability matrix | P3-A | `core/runtime/entry_registry.py` |
| Runtime state dump/restore | P3-A | `brain_memory/runtime_state.py` |
| CDG before irreversible mutation | P1 | Pending |
| Full-loop-only write policy for `/v1/capture` | P1 | Pending |

### 2. Memory System

| Item | Priority | Status |
|------|----------|--------|
| Belief/Narrative block persist | P0 | Done |
| Schema version on blocks | P3-B | Pending |
| `migrate_narrative.py` | P3-A | Done |
| Memory provenance fields | P3-B | Partial |
| Poisoning detection | P2 | Pending |

### 3. Recall Engine

| Item | Priority | Status |
|------|----------|--------|
| RecallPipeline | P0 | Done |
| Attention boost in ranking | P3-A | Done |
| Recall explainability | P3-A | `last_recall_explain` |
| Recall@K benchmark | P3-A | Benchmark suite |

### 4. Attention

| Item | Priority | Status |
|------|----------|--------|
| Affects recall ranking | P3-A | Done |
| Prompt diff test | P3-A | `test_attention_prompt_diff.py` |
| Attention on/off benchmark | P3-A | Benchmark suite |
| Drift monitoring | P3-B | Pending |

### 5. Reflection

| Item | Priority | Status |
|------|----------|--------|
| Narrative block write | P1 | Done |
| Reflection on/off benchmark | P3-A | Benchmark suite |
| Loop protection (cooldown) | P3-A | Config `reflection_cooldown_turns` |
| Quality scoring | P3-B | Pending |

### 6. Governance

| Item | Priority | Status |
|------|----------|--------|
| GovernancePipeline | P0 | Done |
| Values modes OBSERVE/FLAG/REWRITE/BLOCK | P3-A | Config-driven |
| write_gate_threshold wired | P3-A | From config |
| Red-team injection suite | P3-C | Expanding |

### 7. Storage

| Item | Priority | Status |
|------|----------|--------|
| Lance roundtrip test | P3-A | `test_lance_roundtrip.py` |
| Atomic block writes | P3-B | Pending |
| Backup/restore automation | P3-B | Pending |
| Migration framework CLI | P3-B | Partial scripts |

### 8. Testing

| Item | Priority | Status |
|------|----------|--------|
| 360+ unit/integration | P0 | Done |
| Benchmark CI gate | P3-A | `scripts/run_benchmarks.py` |
| Chaos tests | P3-B | Pending |
| 72h long-run | P3-B | Pending |

### 9. Security

| Item | Priority | Status |
|------|----------|--------|
| JWT/API key | P3-C | Pending |
| Production bypass guard | P3-A | `CNEXUS_ENV=production` |
| Injection tests | P3-A | Expanding |

### 10. Observability

| Item | Priority | Status |
|------|----------|--------|
| Metrics collector | P3-A | `core/observability/metrics.py` |
| Trace correlation ID | P3-A | In `process_interaction` |
| Prometheus export | P3-B | Pending |

### 11. Developer Experience

| Item | Priority | Status |
|------|----------|--------|
| SDK docs v1.1 | P1 | Interface doc |
| Docker compose | P3-B | Pending |
| Upgrade guide | P3-B | Pending |

### 12. Enterprise

| Item | Priority | Status |
|------|----------|--------|
| Multi-tenant | P3-D | Pending |
| Audit dashboard | P3-D | Pending |
| GDPR purge API | P3-D | Pending |

---

## Phased Delivery

### P3-A — Prove effectiveness (current sprint)

Benchmark suite · Attention in recall · Values modes · Observability · Lance test · CI gates

### P3-B — Prove reliability

Atomic storage · Backup · Chaos · Long-run · Docker

### P3-C — Prove security

JWT · RBAC · Red team · Injection hardening

### P3-D — Enterprise

Multi-tenant · Governance UI · Compliance

---

## Release Gates

- **Gate D (P3-A):** Benchmark baseline recorded in `docs/benchmarks/BASELINE.md`  
- **Gate B (P3-B):** Backup restore verified  
- **Gate A (P3-C):** Auth + rate limit on all routes  
- **Gate E (P3-D):** Tenant isolation E2E
