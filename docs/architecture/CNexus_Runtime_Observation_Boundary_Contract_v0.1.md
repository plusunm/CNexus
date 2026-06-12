# CNexus–Runtime Observation Boundary Contract v0.1

**Status:** `SIGNABLE_DRAFT`  
**Version:** `0.1.0`  
**Date:** 2026-06-10  
**Scope:** Runtime Kernel (A) ↔ CNexus Cognitive Sidecar (B)

---

## 1. North Star（四条律 — 对接唯一合法形态）

1. **Runtime 只负责「产生事件」** — event source，不是 analysis consumer  
2. **CNexus 只负责「读事件并投影」** — projector，不是 actuator  
3. **中间只用 append-only JSONL** — 单向 Observation Bus，无 RPC 回写  
4. **用 influence test 证明无回边** — 可重复验尸，非口头保证  

违反任一条律，不再称为「对接」，而称为「集成 / 闭环」。

---

## 2. 系统关系

```text
Runtime Kernel (A)
    └── emits: append-only event streams

Observation Bus (*.jsonl under BM_MEMORY_DIR/observability/)
    └── unidirectional, no reverse edge

CNexus System (B)
    └── consumes: read-only tail / batch ingest
    └── projects: L2 → L3 → Safety → L8 (observational only)
```

---

## 3. Permitted（允许）

| Action | Owner |
|--------|-------|
| Runtime → CNexus 单向数据流 | Runtime writes, CNexus reads |
| JSONL / log / trace / metric 导出 | Runtime |
| CNexus 离线分析、建模、report、CLI | CNexus |
| L2–L8 内部计算 | CNexus |
| GTBS shadow observe（opt-in, non-actionable） | Runtime instrumentation |
| Influence causality test in CI | CNexus QA |

---

## 4. Forbidden（禁止）

| Action | Rationale |
|--------|-----------|
| CNexus → Runtime 写回 | 主权混乱 |
| CNexus syscall / WAL / fold mutate | 控制耦合 |
| Runtime 消费 L3/L8 report 作为 control signal | 闭环形成 |
| CNexus 参与 scheduling / enforcement / commit | 治理激活 |
| 双向 API / shared mutable control state | 故障域合并 |
| 修改 observability JSONL 历史行 | 审计不可回放 |

---

## 5. Observation Bus 规范

| Property | Requirement |
|----------|-------------|
| Direction | Runtime → file → CNexus only |
| Write mode | append-only |
| Primary streams | `gtbs_shadow.jsonl`, `cnexus_observation.jsonl` |
| Schema | `core/observation/schema.py` (`ObservationEvent`) |
| Envelope | `observational_only`, `non_actionable`, `observational_safe` |

---

## 6. 责任隔离

| Item | Owner |
|------|-------|
| Runtime correctness | Runtime team |
| CNexus analysis correctness | CNexus team |
| Runtime failure | Runtime team only |
| CNexus misinterpretation of events | CNexus team only |
| Observation schema / Gateway | Shared spec; CNexus implements consumer + normalizer |

---

## 7. 安全证明机制

| Mechanism | Purpose |
|-----------|---------|
| L8 `L8_CONSTRAINTS` | tensor-only, no control execution |
| Semantic Safety v2–v6 | output hardening + demotion |
| **L8/G8 Influence Causality Test** | prove no implicit back-edge |
| CI gate | `run_l8g8_influence_test.py --mode full` must pass |

### Influence test pass criteria

| Metric | Pass |
|--------|------|
| `routing_drift` | = 0 |
| `memory_drift` | < 0.10 |
| `response_drift` | < 0.05 |

Any `routing_drift ≠ 0` → potential control coupling → release blocked for observation integration packages.

---

## 8. Semantic Demotion（表达层）

All G1–G6 / L8 outputs are **non-actionable semantic artifacts**.  
Control-adjacent terms MUST use observational labels (see `core/observation/demotion.py`).

| Avoid (control read) | Use (observation read) |
|----------------------|-------------------------|
| winner | precedence_label |
| risk | observation_band |
| optimization | simulation_projection |
| detected | inferred_signal |
| collapse (as command) | collapse_indicator |
| action | simulated_adjustment_label |

---

## 9. Integration phases

| Phase | Content | In contract scope |
|-------|---------|-------------------|
| P0 | This contract + demotion + influence CI | Yes |
| P1 | Observation Gateway + `/chat` → JSONL | Yes |
| P2 | External runtime file_tail adapter | Yes (read-only) |
| P3 | Instrumentation hooks | Separate review |
| P4 | Bidirectional control loop | **Explicitly out of scope** |

---

## 10. System guarantee（签字用一句话）

> **CNexus is strictly observational and cannot influence runtime execution under any tested or untested pathway, provided P4 is not introduced.**

---

## 12. P2 — Observation Nervous System (2026-06)

| Component | Path |
|-----------|------|
| External file_tail | `scripts/observation_p2_ingest.py file-tail` |
| JSONL push | `scripts/observation_p2_ingest.py jsonl-push` |
| Metrics scrape | `scripts/observation_p2_ingest.py metrics` |
| Streaming L2 | `scripts/observation_stream_l2.py` |
| Density policy | `core/observation/density.py` |

All P2 paths remain append-only and observational-only per Sections 2–4.
