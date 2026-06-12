"""
Phase C — Monthly Continuity Ecology Report (instrumentation-only).
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from core.governance.ecology.collector import EcologyMetricsCollector
from core.governance.ecology.metrics import ATTRACTOR_LABELS, EcologyMetricsEngine
from core.governance.gtbs.divergence_analysis import DivergenceAnalyzer, _parse_ts
from core.governance.shaping.attribution import ShapingAttributor
from core.governance.semantic_safety.envelope import with_observational_safety


def _iso_month(ts: datetime) -> str:
    return ts.strftime("%Y-%m")


@dataclass
class MonthlyEcologyReport:
    """Phase C monthly ecology observability bundle."""

    attractor_competition_map: Dict[str, Any] = field(default_factory=dict)
    openness_decay_trend: List[Dict[str, Any]] = field(default_factory=list)
    reality_recovery_elasticity_trend: List[Dict[str, Any]] = field(default_factory=list)
    contradiction_persistence_distribution: Dict[str, Any] = field(default_factory=dict)
    continuity_pressure_evolution: List[Dict[str, Any]] = field(default_factory=list)
    ecosystem_stabilization_summary: Dict[str, Any] = field(default_factory=dict)
    instrumentation_only: bool = True
    north_star: str = "Reality-Governed Continuity Ecology"

    def to_dict(self) -> dict[str, Any]:
        return with_observational_safety(
            {
                "phase": "Phase C — Continuity Ecology Observatory",
                "instrumentation_only": self.instrumentation_only,
                "no_enforcement": True,
                "north_star": self.north_star,
                "attractor_competition_map": self.attractor_competition_map,
                "openness_decay_trend": self.openness_decay_trend,
                "reality_recovery_elasticity_trend": self.reality_recovery_elasticity_trend,
                "contradiction_persistence_distribution": self.contradiction_persistence_distribution,
                "continuity_pressure_evolution": self.continuity_pressure_evolution,
                "ecosystem_stabilization_summary": self.ecosystem_stabilization_summary,
            },
            simulation_only=False,
        )


class EcologyObservatoryEngine:
    """
    Monthly ecology report generator.

    Reads ecology_metrics.jsonl + shadow projections. Never feeds runtime (A5).
    """

    METRIC_KEYS = ("acd", "odc", "rre", "cpi", "cpx")

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self._collector = EcologyMetricsCollector(base_dir)
        self._metrics_engine = EcologyMetricsEngine(base_dir)
        self._divergence = DivergenceAnalyzer(base_dir)

    def record_snapshot(self) -> dict[str, Any]:
        snap = self._collector.record_snapshot(self.base_dir)
        return snap.to_dict()

    def generate_monthly_report(
        self,
        metric_history: Optional[Sequence[dict[str, Any]]] = None,
    ) -> MonthlyEcologyReport:
        history = list(
            metric_history if metric_history is not None else self._collector.read_all()
        )
        shadow_rows = self._divergence.load()

        if not history and shadow_rows:
            history = [self._metrics_engine.compute(shadow_rows).to_dict()]

        report = MonthlyEcologyReport()
        report.attractor_competition_map = self._attractor_competition_map(shadow_rows)

        monthly: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: {k: [] for k in self.METRIC_KEYS}
        )
        for row in history:
            ts = _parse_ts(row.get("ts"))
            if not ts:
                continue
            month = _iso_month(ts)
            for key in self.METRIC_KEYS:
                val = row.get(key)
                if val is not None:
                    monthly[month][key].append(float(val))

        months_sorted = sorted(monthly.keys())

        def _monthly_trend(metric: str) -> list[dict[str, Any]]:
            series = []
            prev = None
            for month in months_sorted:
                vals = monthly[month][metric]
                if not vals:
                    continue
                mean = round(statistics.mean(vals), 4)
                direction = "stable"
                if prev is not None:
                    if mean > prev + 0.04:
                        direction = "rising"
                    elif mean < prev - 0.04:
                        direction = "falling"
                series.append(
                    {"month": month, "mean": mean, "samples": len(vals), "direction": direction}
                )
                prev = mean
            return series

        report.openness_decay_trend = _monthly_trend("odc")
        report.reality_recovery_elasticity_trend = _monthly_trend("rre")
        report.continuity_pressure_evolution = _monthly_trend("cpx")

        cpi_vals = [float(r["cpi"]) for r in history if r.get("cpi") is not None]
        report.contradiction_persistence_distribution = {
            "samples": len(cpi_vals),
            "mean": round(statistics.mean(cpi_vals), 4) if cpi_vals else 0.0,
            "max": round(max(cpi_vals), 4) if cpi_vals else 0.0,
            "elevated_count": sum(1 for v in cpi_vals if v >= 0.45),
            "interpretation": "epistemic signal — not runtime fault",
        }

        report.ecosystem_stabilization_summary = self._stabilization_summary(
            history, report, months_sorted
        )
        return report

    def _attractor_competition_map(
        self, shadow_rows: Sequence[dict[str, Any]]
    ) -> dict[str, Any]:
        if not shadow_rows:
            return {"status": "insufficient_data"}

        attributor = ShapingAttributor()
        by_month: dict[str, Counter[str]] = defaultdict(Counter)
        overall: Counter[str] = Counter()

        for row in shadow_rows:
            ts = _parse_ts(row.get("timestamp"))
            if not ts:
                continue
            month = _iso_month(ts)
            classified = attributor.classify_observation(row)
            dominant = max(classified, key=classified.get)
            label = ATTRACTOR_LABELS.get(dominant, dominant)
            by_month[month][label] += 1
            overall[label] += 1

        total = sum(overall.values()) or 1
        shares = {k: round(v / total, 4) for k, v in overall.items()}
        max_share = max(shares.values()) if shares else 0.0

        snap = self._metrics_engine.compute(shadow_rows)
        return {
            "overall_ranking": [
                {"attractor": a, "share": s, "count": overall[a]}
                for a, s in sorted(shares.items(), key=lambda x: x[1], reverse=True)
            ],
            "by_month": {m: dict(c) for m, c in sorted(by_month.items())},
            "acd": snap.acd,
            "monopolistic_risk": (
                "elevated" if max_share >= 0.55 and snap.acd >= 0.45 else "moderate" if max_share >= 0.40 else "low"
            ),
        }

    def _stabilization_summary(
        self,
        history: Sequence[dict[str, Any]],
        report: MonthlyEcologyReport,
        months: List[str],
    ) -> dict[str, Any]:
        if not history:
            return {"status": "insufficient_data"}

        latest = history[-1]
        acd = float(latest.get("acd", 0.0))
        odc = float(latest.get("odc", 0.0))
        rre = float(latest.get("rre", 0.0))
        cpi = float(latest.get("cpi", 0.0))
        cpx = float(latest.get("cpx", 0.0))

        odc_rising = (
            report.openness_decay_trend[-1]["direction"] == "rising"
            if report.openness_decay_trend
            else False
        )
        rre_falling = (
            report.reality_recovery_elasticity_trend[-1]["direction"] == "falling"
            if report.reality_recovery_elasticity_trend
            else False
        )

        def _band(value: float, moderate: float, elevated: float) -> str:
            if value >= elevated:
                return "elevated_observation"
            if value >= moderate:
                return "moderate_observation"
            return "low_observation"

        closure_obs = "elevated_observation" if odc >= 0.45 or (odc_rising and odc >= 0.30) else "low_observation"
        decoupling_obs = "elevated_observation" if rre < 0.35 or rre_falling else "low_observation"
        monopoly_obs = _band(acd, 0.35, 0.50)

        return {
            "months_observed": len(months),
            "latest_metrics": {"acd": acd, "odc": odc, "rre": rre, "cpi": cpi, "cpx": cpx},
            "ecological_observations": {
                "attractor_monopoly_observation": monopoly_obs,
                "self_sealing_observation": closure_obs,
                "reality_decoupling_observation": decoupling_obs,
                "forced_coherence_observation": "elevated_observation" if cpi >= 0.45 else "low_observation",
                "continuity_distortion_observation": "elevated_observation" if cpx >= 0.45 else "low_observation",
            },
            "avoid": [
                "continuity monopolistic attractors",
                "recursive epistemic closure",
            ],
            "interpretation": "heuristic ecology signal — observability never becomes control",
        }
