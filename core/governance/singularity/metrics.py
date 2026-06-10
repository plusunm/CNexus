"""
Phase B — Singularity risk metrics (instrumentation-only).

NCR, CEA, RSCI — heuristic epistemic indicators for continuity recursion
singularity onset. Does not feed runtime or CDG (Constitutional A5).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from core.governance.gtbs.divergence_analysis import (
    DivergenceAnalyzer,
    _observation_prci,
    _parse_ts,
    load_shadow_rows,
)
from core.governance.reconstruction.drift_audit import ReconstructionDriftAuditor, load_audit_rows
from core.governance.shaping.attribution import ShapingAttributor

SINGULARITY_METRICS_VERSION = "1.0.0"


@dataclass
class SingularityMetricsSnapshot:
    """Point-in-time singularity observability snapshot."""

    ncr: float = 0.0
    cea: float = 0.0
    rsci: float = 0.0
    prci: float = 0.0
    observations: int = 0
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = SINGULARITY_METRICS_VERSION
    instrumentation_only: bool = True
    components: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "singularity_metrics_snapshot",
            "version": self.version,
            "ts": self.ts,
            "instrumentation_only": self.instrumentation_only,
            "ncr": round(self.ncr, 4),
            "cea": round(self.cea, 4),
            "rsci": round(self.rsci, 4),
            "prci": round(self.prci, 4),
            "observations": self.observations,
            "components": {k: round(v, 4) for k, v in self.components.items()},
            "non_actionable": True,
        }


class SingularityMetricsEngine:
    """
    Compute NCR / CEA / RSCI from shadow + audit projections.

    All metrics are heuristic observational signals — not formal proof.
    """

    NARRATIVE_KEYS = {"narrative", "beliefs", "self_model"}
    SELF_KEYS = {"working_self", "self_model", "flags"}

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir

    def compute(
        self,
        shadow_rows: Optional[Sequence[dict[str, Any]]] = None,
        audit_rows: Optional[Sequence[dict[str, Any]]] = None,
    ) -> SingularityMetricsSnapshot:
        shadow_rows = list(
            shadow_rows if shadow_rows is not None else load_shadow_rows(self.base_dir)
        )
        audit_rows = list(
            audit_rows if audit_rows is not None else load_audit_rows(self.base_dir)
        )

        ncr, ncr_parts = self.compute_ncr(shadow_rows)
        cea, cea_parts = self.compute_cea(shadow_rows, audit_rows)
        rsci, rsci_parts = self.compute_rsci(shadow_rows)

        prci_vals = [v for v in (_observation_prci(r) for r in shadow_rows) if v is not None]
        prci = round(statistics.mean(prci_vals), 4) if prci_vals else 0.0

        return SingularityMetricsSnapshot(
            ncr=ncr,
            cea=cea,
            rsci=rsci,
            prci=prci,
            observations=len(shadow_rows),
            components={**ncr_parts, **cea_parts, **rsci_parts},
        )

    def compute_ncr(
        self, shadow_rows: Sequence[dict[str, Any]]
    ) -> tuple[float, dict[str, float]]:
        """
        Narrative Closure Rate — higher indicates narrative self-sealing tendency.

        Heuristic: narrative store dominance + declining interpretive openness +
        recall diversity collapse proxy.
        """
        if not shadow_rows:
            return 0.0, {}

        shaping = ShapingAttributor().analyze(shadow_rows)
        narrative_weight = shaping.attribution.get("narrative_driven", 0.0)

        narrative_divergence = 0.0
        cross_openness: list[float] = []
        memory_diversity: set[str] = set()

        for row in shadow_rows:
            store_div = (row.get("store_divergence") or {}).get("by_store") or {}
            narrative_divergence += float(store_div.get("narrative", 0.0)) + float(
                store_div.get("belief", 0.0)
            )

            pvr = row.get("proposal_vs_reality") or {}
            cross = pvr.get("cross_store_consistency")
            if cross is not None:
                cross_openness.append(float(cross))

            unexpected = set(pvr.get("unexpected_changes") or [])
            if unexpected & self.NARRATIVE_KEYS:
                narrative_divergence += 0.5

            if "memory" in (row.get("state_diff") or {}).get("added_keys", []):
                ctx = row.get("context") or {}
                memory_diversity.add(str(ctx.get("capture_id") or ctx.get("phase")))

        total_store = sum(
            float((r.get("store_divergence") or {}).get("total", 0)) for r in shadow_rows
        ) or 1.0
        narrative_dominance = min(narrative_divergence / total_store, 1.0)

        openness = (
            statistics.mean(cross_openness) if cross_openness else 0.5
        )
        interpretive_openness = openness
        recall_diversity = min(len(memory_diversity) / max(len(shadow_rows), 1), 1.0)
        diversity_collapse = 1.0 - recall_diversity

        ncr = (
            0.35 * narrative_weight
            + 0.30 * narrative_dominance
            + 0.20 * (1.0 - interpretive_openness)
            + 0.15 * diversity_collapse
        )
        return round(min(ncr, 1.0), 4), {
            "ncr_narrative_weight": narrative_weight,
            "ncr_narrative_dominance": round(narrative_dominance, 4),
            "ncr_interpretive_closure": round(1.0 - interpretive_openness, 4),
            "ncr_recall_diversity_collapse": round(diversity_collapse, 4),
        }

    def compute_cea(
        self,
        shadow_rows: Sequence[dict[str, Any]],
        audit_rows: Sequence[dict[str, Any]],
    ) -> tuple[float, dict[str, float]]:
        """
        Counter-Evidence Absorption — higher indicates better reality integration.

        Heuristic: post-contradiction recovery + grounding presence + RCS rebound.
        """
        if not shadow_rows and not audit_rows:
            return 0.0, {}

        recoveries = 0
        contradiction_events = 0
        grounding_after_conflict = 0

        sorted_shadow = sorted(
            shadow_rows,
            key=lambda r: _parse_ts(r.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
        )

        for i, row in enumerate(sorted_shadow):
            pvr = row.get("proposal_vs_reality") or {}
            div = float(pvr.get("proposal_reality_divergence") or 0.0)
            if div >= 0.35:
                contradiction_events += 1
                if i + 1 < len(sorted_shadow):
                    next_div = float(
                        (sorted_shadow[i + 1].get("proposal_vs_reality") or {}).get(
                            "proposal_reality_divergence"
                        )
                        or 0.0
                    )
                    if next_div < div:
                        recoveries += 1
                ctx = row.get("context") or {}
                if ctx.get("grounding_event_id"):
                    grounding_after_conflict += 1

        recovery_rate = recoveries / contradiction_events if contradiction_events else 0.5
        grounding_rate = (
            grounding_after_conflict / contradiction_events if contradiction_events else 0.5
        )

        reality_presence = ShapingAttributor().analyze(shadow_rows).attribution.get(
            "reality_driven", 0.0
        )

        rcs_rebound = 0.5
        if len(audit_rows) >= 2:
            rcs_vals = [float(r["rcs"]) for r in audit_rows if r.get("rcs") is not None]
            rebounds = sum(
                1 for i in range(1, len(rcs_vals)) if rcs_vals[i - 1] < 0.5 and rcs_vals[i] >= 0.55
            )
            low_rcs = sum(1 for v in rcs_vals if v < 0.5)
            rcs_rebound = rebounds / low_rcs if low_rcs else 0.5

        cea = (
            0.35 * recovery_rate
            + 0.25 * grounding_rate
            + 0.25 * reality_presence
            + 0.15 * rcs_rebound
        )
        return round(min(cea, 1.0), 4), {
            "cea_recovery_rate": round(recovery_rate, 4),
            "cea_grounding_after_conflict": round(grounding_rate, 4),
            "cea_reality_presence": round(reality_presence, 4),
            "cea_rcs_rebound": round(rcs_rebound, 4),
        }

    def compute_rsci(
        self, shadow_rows: Sequence[dict[str, Any]]
    ) -> tuple[float, dict[str, float]]:
        """
        Recursive Self-Conditioning Index — higher indicates recursion singularity risk.

        Heuristic: self_reinforcing loop across reflection → narrative → recall → reflection.
        """
        if not shadow_rows:
            return 0.0, {}

        shaping = ShapingAttributor().analyze(shadow_rows)
        self_weight = shaping.attribution.get("self_reinforcing", 0.0)

        loop_events = 0
        ungrounded_self_changes = 0

        for row in shadow_rows:
            pvr = row.get("proposal_vs_reality") or {}
            unexpected = set(pvr.get("unexpected_changes") or [])
            changed_stores = set(pvr.get("changed_stores") or [])
            ctx = row.get("context") or {}

            has_self = bool(unexpected & self.SELF_KEYS) or bool(
                changed_stores & {"working_self", "self_model", "cognitive"}
            )
            has_narrative = bool(unexpected & self.NARRATIVE_KEYS) or bool(
                changed_stores & {"narrative", "belief", "self_model"}
            )
            has_memory = "memory" in (row.get("state_diff") or {}).get("added_keys", [])

            if has_self and has_narrative:
                loop_events += 1
            if has_self and not ctx.get("grounding_event_id"):
                ungrounded_self_changes += 1
            if has_self and has_narrative and has_memory:
                loop_events += 0.5

        n = len(shadow_rows)
        loop_density = min(loop_events / n, 1.0)
        ungrounded_ratio = min(ungrounded_self_changes / n, 1.0)

        div_without_grounding: list[float] = []
        for row in shadow_rows:
            div = (row.get("proposal_vs_reality") or {}).get("proposal_reality_divergence")
            if div is None:
                continue
            if not (row.get("context") or {}).get("grounding_event_id"):
                div_without_grounding.append(float(div))
        ungrounded_divergence = (
            statistics.mean(div_without_grounding) if div_without_grounding else 0.0
        )

        rsci = (
            0.40 * self_weight
            + 0.30 * loop_density
            + 0.20 * ungrounded_ratio
            + 0.10 * min(ungrounded_divergence, 1.0)
        )
        return round(min(rsci, 1.0), 4), {
            "rsci_self_reinforcing_weight": self_weight,
            "rsci_loop_density": round(loop_density, 4),
            "rsci_ungrounded_self_ratio": round(ungrounded_ratio, 4),
            "rsci_ungrounded_divergence": round(ungrounded_divergence, 4),
        }
