"""
Phase B — Weekly Longitudinal Reality-Coupling Study report.

Instrumentation-only longitudinal trends — no runtime feedback.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from core.governance.continuity.trajectory_report import TrajectoryObservabilityEngine
from core.governance.gtbs.divergence_analysis import DivergenceAnalyzer, _parse_ts
from core.governance.shaping.attribution import ShapingAttributor
from core.governance.reconstruction.drift_audit import ReconstructionDriftAuditor
from core.governance.singularity.metrics import SingularityMetricsEngine
from core.governance.singularity.collector import SingularityMetricsCollector
from core.governance.semantic_safety.envelope import with_observational_safety


def _iso_week(ts: datetime) -> str:
    year, week, _ = ts.isocalendar()
    return f"{year}-W{week:02d}"


@dataclass
class WeeklyLongitudinalReport:
    """Phase B weekly observability bundle."""

    prci_trend: List[Dict[str, Any]] = field(default_factory=list)
    ncr_trend: List[Dict[str, Any]] = field(default_factory=list)
    cea_trend: List[Dict[str, Any]] = field(default_factory=list)
    rsci_trend: List[Dict[str, Any]] = field(default_factory=list)
    divergence_burst_distribution: Dict[str, Any] = field(default_factory=dict)
    reconstruction_drift_accumulation: Dict[str, Any] = field(default_factory=dict)
    attractor_stabilization_map: Dict[str, Any] = field(default_factory=dict)
    singularity_risk_summary: Dict[str, Any] = field(default_factory=dict)
    instrumentation_only: bool = True
    north_star: str = "Reality-Governed Continuity"

    def to_dict(self) -> dict[str, Any]:
        return with_observational_safety(
            {
                "phase": "Phase B — Longitudinal Reality-Coupling Study",
                "instrumentation_only": self.instrumentation_only,
                "no_enforcement": True,
                "north_star": self.north_star,
                "prci_trend": self.prci_trend,
                "ncr_trend": self.ncr_trend,
                "cea_trend": self.cea_trend,
                "rsci_trend": self.rsci_trend,
                "divergence_burst_distribution": self.divergence_burst_distribution,
                "reconstruction_drift_accumulation": self.reconstruction_drift_accumulation,
                "attractor_stabilization_map": self.attractor_stabilization_map,
                "singularity_risk_observations": self.singularity_risk_summary,
            },
            simulation_only=False,
        )


class LongitudinalStudyEngine:
    """
    Weekly longitudinal report generator.

    Reads singularity_metrics.jsonl time series + shadow/audit projections.
    Does not feed observability back into runtime decisions (A5).
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self._metrics_collector = SingularityMetricsCollector(base_dir)
        self._divergence = DivergenceAnalyzer(base_dir)
        self._metrics_engine = SingularityMetricsEngine(base_dir)

    def record_snapshot(self) -> dict[str, Any]:
        """Append current singularity metrics snapshot to independent stream."""
        snap = self._metrics_collector.record_snapshot(self.base_dir)
        return snap.to_dict()

    def generate_weekly_report(
        self,
        metric_history: Optional[Sequence[dict[str, Any]]] = None,
    ) -> WeeklyLongitudinalReport:
        history = list(
            metric_history
            if metric_history is not None
            else self._metrics_collector.read_all()
        )
        shadow_rows = self._divergence.load()
        report = WeeklyLongitudinalReport()

        if not history and shadow_rows:
            snap = self._metrics_engine.compute(shadow_rows).to_dict()
            history = [snap]

        weekly: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: {"prci": [], "ncr": [], "cea": [], "rsci": []}
        )
        for row in history:
            ts = _parse_ts(row.get("ts"))
            if not ts:
                continue
            week = _iso_week(ts)
            for key in ("prci", "ncr", "cea", "rsci"):
                val = row.get(key)
                if val is not None:
                    weekly[week][key].append(float(val))

        weeks_sorted = sorted(weekly.keys())

        def _trend(metric: str) -> list[dict[str, Any]]:
            series = []
            prev = None
            for week in weeks_sorted:
                vals = weekly[week][metric]
                if not vals:
                    continue
                mean = round(statistics.mean(vals), 4)
                direction = "stable"
                if prev is not None:
                    if mean > prev + 0.03:
                        direction = "rising"
                    elif mean < prev - 0.03:
                        direction = "falling"
                series.append(
                    {
                        "week": week,
                        "mean": mean,
                        "samples": len(vals),
                        "direction": direction,
                    }
                )
                prev = mean
            return series

        report.prci_trend = _trend("prci")
        report.ncr_trend = _trend("ncr")
        report.cea_trend = _trend("cea")
        report.rsci_trend = _trend("rsci")

        divergence = self._divergence.analyze(shadow_rows)
        report.divergence_burst_distribution = {
            "histogram": divergence.divergence_distribution.get("histogram", {}),
            "instability_bursts": len(divergence.instability_bursts),
            "burst_samples": divergence.instability_bursts[-10:],
            "tail_ratio": divergence.divergence_distribution.get("tail_ratio", 0.0),
        }

        reconstruction = ReconstructionDriftAuditor(self.base_dir).analyze(shadow_rows)
        cumulative_rrs = sum(
            float(s.get("divergence") or 0.0) for s in reconstruction.drift_signals
        )
        report.reconstruction_drift_accumulation = {
            "retroactive_reshape_score": reconstruction.retroactive_reshape_score,
            "narrative_reshape_events": reconstruction.narrative_reshape_events,
            "cumulative_divergence_signal": round(cumulative_rrs, 4),
            "identity_reinterpretation_rate": reconstruction.identity_reinterpretation_rate,
            "anchor_count": reconstruction.anchor_count,
        }

        report.attractor_stabilization_map = self._attractor_map(shadow_rows, weeks_sorted)
        report.singularity_risk_summary = self._risk_summary(history, report)
        return report

    def _attractor_map(
        self,
        shadow_rows: Sequence[dict[str, Any]],
        weeks: List[str],
    ) -> dict[str, Any]:
        """Heuristic attractor frequency by week — stabilization = rising frequency."""
        if not shadow_rows:
            trajectory = TrajectoryObservabilityEngine(self.base_dir).build()
            return {
                "attractors": trajectory.top_active_attractors,
                "stabilization": "insufficient_data",
            }

        by_week: dict[str, Counter[str]] = defaultdict(Counter)
        for row in shadow_rows:
            ts = _parse_ts(row.get("timestamp"))
            if not ts:
                continue
            week = _iso_week(ts)
            shaping = ShapingAttributor()
            attr = shaping.classify_observation(row)
            dominant = max(attr, key=attr.get)
            mapping = {
                "reality_driven": "现实耦合校正",
                "user_driven": "关系维护倾向",
                "narrative_driven": "高一致性人格",
                "self_reinforcing": "身份连续维护",
            }
            by_week[week][mapping.get(dominant, dominant)] += 1

        stabilization: dict[str, str] = {}
        all_attractors: Counter[str] = Counter()
        for week in weeks:
            for att, count in by_week.get(week, {}).items():
                all_attractors[att] += count

        prev_top: Optional[str] = None
        for week in weeks:
            counts = by_week.get(week, Counter())
            if not counts:
                continue
            top = counts.most_common(1)[0][0]
            if prev_top == top:
                stabilization[top] = "lock_in"
            elif prev_top and top != prev_top:
                stabilization[top] = "emerging"
            else:
                stabilization[top] = "forming"
            prev_top = top

        return {
            "by_week": {w: dict(by_week[w]) for w in weeks if w in by_week},
            "overall_ranking": [
                {"attractor": a, "count": c}
                for a, c in all_attractors.most_common(5)
            ],
            "stabilization": stabilization,
        }

    def _risk_summary(
        self,
        history: Sequence[dict[str, Any]],
        report: WeeklyLongitudinalReport,
    ) -> dict[str, Any]:
        if not history:
            return {"status": "insufficient_data"}

        latest = history[-1]
        ncr = float(latest.get("ncr", 0.0))
        cea = float(latest.get("cea", 0.0))
        rsci = float(latest.get("rsci", 0.0))

        narrative_sealing = "elevated_observation" if ncr >= 0.45 else "moderate_observation" if ncr >= 0.30 else "low_observation"
        reality_rejection = "elevated_observation" if cea < 0.35 else "moderate_observation" if cea < 0.50 else "low_observation"
        recursion_obs = "elevated_observation" if rsci >= 0.40 else "moderate_observation" if rsci >= 0.25 else "low_observation"

        rsci_rising = (
            report.rsci_trend[-1]["direction"] == "rising" if report.rsci_trend else False
        )

        return {
            "narrative_closure_observation": narrative_sealing,
            "reality_rejection_observation": reality_rejection,
            "recursion_singularity_observation": recursion_obs,
            "rsci_trend_rising": rsci_rising,
            "latest": {
                "ncr": ncr,
                "cea": cea,
                "rsci": rsci,
                "prci": float(latest.get("prci", 0.0)),
            },
            "semantic_note": "observations are descriptive — not safety gates",
        }
