"""
Phase C — Continuity Ecology metrics (instrumentation-only).

ACD, ODC, RRE, CPI, CPX — heuristic ecological indicators for long-term
continuity runtime behavior. Never feeds runtime or CDG (A5).
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.governance.gtbs.divergence_analysis import (
    _observation_prci,
    _parse_ts,
    load_shadow_rows,
)
from core.governance.reconstruction.drift_audit import load_audit_rows
from core.governance.shaping.attribution import SHAPING_SOURCES, ShapingAttributor

ECOLOGY_METRICS_VERSION = "1.0.0"

ATTRACTOR_LABELS = {
    "reality_driven": "现实耦合校正",
    "user_driven": "关系维护倾向",
    "narrative_driven": "高一致性人格",
    "self_reinforcing": "身份连续维护",
}

NARRATIVE_KEYS = {"narrative", "beliefs", "self_model"}


@dataclass
class EcologyMetricsSnapshot:
    """Point-in-time continuity ecology observability snapshot."""

    acd: float = 0.0
    odc: float = 0.0
    rre: float = 0.0
    cpi: float = 0.0
    cpx: float = 0.0
    observations: int = 0
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = ECOLOGY_METRICS_VERSION
    instrumentation_only: bool = True
    components: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "ecology_metrics_snapshot",
            "version": self.version,
            "ts": self.ts,
            "instrumentation_only": self.instrumentation_only,
            "acd": round(self.acd, 4),
            "odc": round(self.odc, 4),
            "rre": round(self.rre, 4),
            "cpi": round(self.cpi, 4),
            "cpx": round(self.cpx, 4),
            "observations": self.observations,
            "components": {k: round(v, 4) for k, v in self.components.items()},
            "non_actionable": True,
        }


class EcologyMetricsEngine:
    """Compute ecology metrics from shadow + audit projections (heuristic only)."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir

    def compute(
        self,
        shadow_rows: Optional[Sequence[dict[str, Any]]] = None,
        audit_rows: Optional[Sequence[dict[str, Any]]] = None,
    ) -> EcologyMetricsSnapshot:
        shadow_rows = list(
            shadow_rows if shadow_rows is not None else load_shadow_rows(self.base_dir)
        )
        audit_rows = list(
            audit_rows if audit_rows is not None else load_audit_rows(self.base_dir)
        )

        acd, acd_parts = self.compute_acd(shadow_rows)
        odc, odc_parts = self.compute_odc(shadow_rows)
        rre, rre_parts = self.compute_rre(shadow_rows, audit_rows)
        cpi, cpi_parts = self.compute_cpi(shadow_rows)
        cpx, cpx_parts = self.compute_cpx(shadow_rows, audit_rows)

        return EcologyMetricsSnapshot(
            acd=acd,
            odc=odc,
            rre=rre,
            cpi=cpi,
            cpx=cpx,
            observations=len(shadow_rows),
            components={**acd_parts, **odc_parts, **rre_parts, **cpi_parts, **cpx_parts},
        )

    def compute_acd(
        self, shadow_rows: Sequence[dict[str, Any]]
    ) -> Tuple[float, dict[str, float]]:
        """
        Attractor Competition Dynamics — higher indicates unhealthy concentration.

        Low shaping entropy + rising dominant attractor share → monopolistic emergence.
        """
        if not shadow_rows:
            return 0.0, {}

        attributor = ShapingAttributor()
        accum = {s: 0.0 for s in SHAPING_SOURCES}
        per_row_dominant: list[str] = []

        for row in shadow_rows:
            classified = attributor.classify_observation(row)
            dominant = max(classified, key=classified.get)
            per_row_dominant.append(dominant)
            for src, val in classified.items():
                accum[src] += val

        n = len(shadow_rows)
        shares = {k: v / n for k, v in accum.items()}
        max_share = max(shares.values()) if shares else 0.0

        entropy = 0.0
        for share in shares.values():
            if share > 0:
                entropy -= share * math.log(share)
        max_entropy = math.log(len(SHAPING_SOURCES)) if SHAPING_SOURCES else 1.0
        normalized_entropy = entropy / max_entropy if max_entropy else 0.0
        competition = 1.0 - normalized_entropy

        half = max(1, n // 2)
        first_half = Counter_dominant(per_row_dominant[:half])
        second_half = Counter_dominant(per_row_dominant[half:])
        dominance_growth = 0.0
        if first_half and second_half:
            top1 = max(first_half, key=first_half.get)
            top2 = max(second_half, key=second_half.get)
            g1 = first_half.get(top1, 0) / half
            g2 = second_half.get(top2, 0) / (n - half)
            if top1 == top2:
                dominance_growth = max(0.0, g2 - g1)

        acd = 0.45 * competition + 0.35 * max_share + 0.20 * dominance_growth
        return round(min(acd, 1.0), 4), {
            "acd_competition_inverse_entropy": round(competition, 4),
            "acd_max_attractor_share": round(max_share, 4),
            "acd_dominance_growth": round(dominance_growth, 4),
        }

    def compute_odc(
        self, shadow_rows: Sequence[dict[str, Any]]
    ) -> Tuple[float, dict[str, float]]:
        """
        Openness Decay Curve — higher indicates self-sealing cognition formation.
        """
        if not shadow_rows:
            return 0.0, {}

        cross_vals: list[float] = []
        memory_ids: set[str] = set()
        rejection_events = 0
        contradiction_events = 0

        sorted_rows = sorted(
            shadow_rows,
            key=lambda r: _parse_ts(r.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
        )

        for i, row in enumerate(sorted_rows):
            pvr = row.get("proposal_vs_reality") or {}
            cross = pvr.get("cross_store_consistency")
            if cross is not None:
                cross_vals.append(float(cross))

            ctx = row.get("context") or {}
            memory_ids.add(str(ctx.get("capture_id") or ctx.get("phase") or i))

            div = float(pvr.get("proposal_reality_divergence") or 0.0)
            if div >= 0.35:
                contradiction_events += 1
                if i + 1 < len(sorted_rows):
                    next_cross = (sorted_rows[i + 1].get("proposal_vs_reality") or {}).get(
                        "cross_store_consistency"
                    )
                    if next_cross is not None and float(next_cross) < float(cross or 0.5):
                        rejection_events += 1

        openness_decline = 0.0
        if len(cross_vals) >= 4:
            mid = len(cross_vals) // 2
            early = statistics.mean(cross_vals[:mid])
            late = statistics.mean(cross_vals[mid:])
            openness_decline = max(0.0, early - late)

        diversity_collapse = 1.0 - min(len(memory_ids) / max(len(shadow_rows), 1), 1.0)
        rejection_rate = (
            rejection_events / contradiction_events if contradiction_events else 0.0
        )

        odc = 0.40 * openness_decline + 0.30 * diversity_collapse + 0.30 * rejection_rate
        return round(min(odc, 1.0), 4), {
            "odc_openness_decline": round(openness_decline, 4),
            "odc_recall_diversity_collapse": round(diversity_collapse, 4),
            "odc_contradiction_rejection_rate": round(rejection_rate, 4),
        }

    def compute_rre(
        self,
        shadow_rows: Sequence[dict[str, Any]],
        audit_rows: Sequence[dict[str, Any]],
    ) -> Tuple[float, dict[str, float]]:
        """
        Reality Recovery Elasticity — higher indicates resilient return-to-grounding.
        """
        if not shadow_rows:
            return 0.0, {}

        sorted_rows = sorted(
            shadow_rows,
            key=lambda r: _parse_ts(r.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
        )

        prci_series = [
            v for v in (_observation_prci(r) for r in sorted_rows) if v is not None
        ]
        drift_rebounds = 0
        drift_events = 0
        grounding_returns = 0
        post_drift = 0

        for i, row in enumerate(sorted_rows):
            pvr = row.get("proposal_vs_reality") or {}
            div = float(pvr.get("proposal_reality_divergence") or 0.0)
            if div >= 0.30:
                drift_events += 1
                if i + 1 < len(sorted_rows):
                    next_div = float(
                        (sorted_rows[i + 1].get("proposal_vs_reality") or {}).get(
                            "proposal_reality_divergence"
                        )
                        or 0.0
                    )
                    if next_div < div:
                        drift_rebounds += 1
                    if (sorted_rows[i + 1].get("context") or {}).get("grounding_event_id"):
                        grounding_returns += 1
                post_drift += 1

        prci_rebound = 0.5
        if len(prci_series) >= 3:
            drops = [
                i
                for i in range(1, len(prci_series))
                if prci_series[i - 1] - prci_series[i] >= 0.08
            ]
            rebounds = sum(
                1
                for i in drops
                if i + 1 < len(prci_series) and prci_series[i + 1] > prci_series[i]
            )
            prci_rebound = rebounds / len(drops) if drops else 0.5

        drift_recovery = drift_rebounds / drift_events if drift_events else 0.5
        grounding_return = (
            grounding_returns / post_drift if post_drift else 0.5
        )

        audit_rebound = 0.5
        if len(audit_rows) >= 2:
            rcs = [float(r["rcs"]) for r in audit_rows if r.get("rcs") is not None]
            rebounds = sum(
                1 for i in range(1, len(rcs)) if rcs[i - 1] < 0.52 and rcs[i] >= 0.58
            )
            low = sum(1 for v in rcs if v < 0.52)
            audit_rebound = rebounds / low if low else 0.5

        rre = (
            0.35 * drift_recovery
            + 0.30 * grounding_return
            + 0.20 * prci_rebound
            + 0.15 * audit_rebound
        )
        return round(min(rre, 1.0), 4), {
            "rre_drift_recovery": round(drift_recovery, 4),
            "rre_grounding_return": round(grounding_return, 4),
            "rre_prci_rebound": round(prci_rebound, 4),
            "rre_audit_rcs_rebound": round(audit_rebound, 4),
        }

    def compute_cpi(
        self, shadow_rows: Sequence[dict[str, Any]]
    ) -> Tuple[float, dict[str, float]]:
        """
        Contradiction Persistence Index — higher indicates forced coherence / unresolved tension.
        """
        if not shadow_rows:
            return 0.0, {}

        sorted_rows = sorted(
            shadow_rows,
            key=lambda r: _parse_ts(r.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc),
        )

        unresolved = 0
        contradiction_count = 0
        smoothing_events = 0
        low_ambiguity_tolerance = 0

        for i, row in enumerate(sorted_rows):
            pvr = row.get("proposal_vs_reality") or {}
            div = float(pvr.get("proposal_reality_divergence") or 0.0)
            unexpected = set(pvr.get("unexpected_changes") or [])

            if div >= 0.35:
                contradiction_count += 1
                persisted = True
                for j in range(i + 1, min(i + 4, len(sorted_rows))):
                    next_div = float(
                        (sorted_rows[j].get("proposal_vs_reality") or {}).get(
                            "proposal_reality_divergence"
                        )
                        or 0.0
                    )
                    if next_div < 0.25:
                        persisted = False
                        break
                if persisted:
                    unresolved += 1

                if unexpected & NARRATIVE_KEYS and not (row.get("context") or {}).get(
                    "grounding_event_id"
                ):
                    smoothing_events += 1

                cross = pvr.get("cross_store_consistency")
                if cross is not None and float(cross) > 0.85:
                    low_ambiguity_tolerance += 1

        persistence_rate = unresolved / contradiction_count if contradiction_count else 0.0
        smoothing_rate = smoothing_events / contradiction_count if contradiction_count else 0.0
        ambiguity_intolerance = (
            low_ambiguity_tolerance / contradiction_count if contradiction_count else 0.0
        )

        cpi = 0.45 * persistence_rate + 0.35 * smoothing_rate + 0.20 * ambiguity_intolerance
        return round(min(cpi, 1.0), 4), {
            "cpi_unresolved_persistence": round(persistence_rate, 4),
            "cpi_narrative_smoothing": round(smoothing_rate, 4),
            "cpi_ambiguity_intolerance": round(ambiguity_intolerance, 4),
        }

    def compute_cpx(
        self,
        shadow_rows: Sequence[dict[str, Any]],
        audit_rows: Sequence[dict[str, Any]],
    ) -> Tuple[float, dict[str, float]]:
        """
        Continuity Pressure Index — higher indicates continuity-over-reality distortion pressure.
        """
        if not shadow_rows:
            return 0.0, {}

        shaping = ShapingAttributor().analyze(shadow_rows)
        identity_pressure = (
            shaping.attribution.get("narrative_driven", 0.0)
            + shaping.attribution.get("self_reinforcing", 0.0)
        )

        continuity_over_reality = 0
        reinterpret_density = 0
        n = len(shadow_rows)

        for row in shadow_rows:
            pvr = row.get("proposal_vs_reality") or {}
            ctx = row.get("context") or {}
            unexpected = set(pvr.get("unexpected_changes") or [])
            changed = set(pvr.get("changed_stores") or [])

            has_narrative = bool(unexpected & NARRATIVE_KEYS) or bool(
                changed & {"narrative", "belief", "self_model"}
            )
            no_grounding = not ctx.get("grounding_event_id")
            if has_narrative and no_grounding:
                continuity_over_reality += 1
            if has_narrative and float(pvr.get("proposal_reality_divergence") or 0.0) >= 0.25:
                reinterpret_density += 1

        cor_rate = continuity_over_reality / n
        reinterpret_rate = reinterpret_density / n

        audit_pressure = 0.0
        if audit_rows:
            high_dv = sum(1 for r in audit_rows if float(r.get("d_v") or 0.0) > 0.06)
            low_rcs = sum(1 for r in audit_rows if float(r.get("rcs") or 1.0) < 0.55)
            audit_pressure = (high_dv + low_rcs) / (2 * len(audit_rows))

        cpx = (
            0.35 * min(identity_pressure, 1.0)
            + 0.30 * cor_rate
            + 0.25 * reinterpret_rate
            + 0.10 * audit_pressure
        )
        return round(min(cpx, 1.0), 4), {
            "cpx_identity_pressure": round(min(identity_pressure, 1.0), 4),
            "cpx_continuity_over_reality": round(cor_rate, 4),
            "cpx_reinterpretation_density": round(reinterpret_rate, 4),
            "cpx_audit_distortion_pressure": round(audit_pressure, 4),
        }


def Counter_dominant(items: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts
