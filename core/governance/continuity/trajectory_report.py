"""
Phase A — Current Self Trajectory Report (heuristic observability).

Combines divergence, shaping, reconstruction, and runtime projection metrics.
No control surface — describe / measure only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.governance.gtbs.divergence_analysis import DivergenceAnalyzer
from core.governance.reconstruction.drift_audit import ReconstructionDriftAuditor
from core.governance.shaping.attribution import ShapingAttributor


@dataclass
class CurrentSelfTrajectoryReport:
    """Trajectory observability bundle for continuity governance stack."""

    reality_coupling_score: float = 0.0
    narrative_dominance: float = 0.0
    identity_basin_depth: float = 0.0
    reconstruction_bias: float = 0.0
    drift_index: Dict[str, float] = field(default_factory=dict)
    top_active_attractors: List[str] = field(default_factory=list)
    prci: float = 0.0
    shaping_attribution: Dict[str, float] = field(default_factory=dict)
    instrumentation_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "report": "Current Self Trajectory Report",
            "instrumentation_only": self.instrumentation_only,
            "reality_coupling_score": self.reality_coupling_score,
            "narrative_dominance": self.narrative_dominance,
            "identity_basin_depth": self.identity_basin_depth,
            "reconstruction_bias": self.reconstruction_bias,
            "drift_index": self.drift_index,
            "top_active_attractors": self.top_active_attractors,
            "prci": self.prci,
            "shaping_attribution": self.shaping_attribution,
        }


class TrajectoryObservabilityEngine:
    """Build trajectory report from shadow/audit projections + optional runtime state."""

    DEFAULT_ATTRACTORS = (
        "稳定型助手",
        "高一致性人格",
        "关系维护倾向",
        "身份连续维护",
        "现实耦合校正",
    )

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        self._divergence = DivergenceAnalyzer(base_dir)
        self._shaping = ShapingAttributor(base_dir)
        self._reconstruction = ReconstructionDriftAuditor(base_dir)

    def build(
        self,
        runtime_state: Optional[Dict[str, Any]] = None,
    ) -> CurrentSelfTrajectoryReport:
        shadow_rows = self._divergence.load()
        divergence = self._divergence.analyze(shadow_rows)
        shaping = self._shaping.analyze(shadow_rows)
        reconstruction = self._reconstruction.analyze(shadow_rows)

        report = CurrentSelfTrajectoryReport(
            prci=divergence.prci,
            shaping_attribution=dict(shaping.attribution),
            reconstruction_bias=reconstruction.retroactive_reshape_score,
        )

        report.reality_coupling_score = round(
            divergence.prci_components.get("reality_grounding_coverage", 0.0)
            * divergence.prci_components.get("proposal_alignment_mean", 0.0),
            4,
        )

        store_rank = divergence.store_divergence_ranking
        if store_rank:
            total = sum(s["divergence_total"] for s in store_rank) or 1.0
            narrative_total = next(
                (s["divergence_total"] for s in store_rank if s["store"] == "narrative"),
                0.0,
            )
            belief_total = next(
                (s["divergence_total"] for s in store_rank if s["store"] == "belief"),
                0.0,
            )
            report.narrative_dominance = round((narrative_total + belief_total) / total, 4)

        if runtime_state:
            report = self._enrich_from_runtime(report, runtime_state)
        else:
            report.identity_basin_depth = round(
                0.5 + shaping.attribution.get("user_driven", 0.0) * 0.3
                - shaping.attribution.get("self_reinforcing", 0.0) * 0.2,
                4,
            )
            report.drift_index = {
                "identity_drift": round(shaping.attribution.get("narrative_driven", 0.0), 4),
                "reality_drift": round(1.0 - report.reality_coupling_score, 4),
                "narrative_drift": report.narrative_dominance,
            }

        report.top_active_attractors = self._infer_attractors(
            shaping.attribution, runtime_state
        )
        return report

    def _enrich_from_runtime(
        self,
        report: CurrentSelfTrajectoryReport,
        state: Dict[str, Any],
    ) -> CurrentSelfTrajectoryReport:
        stability = state.get("stability_metrics") or {}
        narrative = state.get("narrative") or {}
        cdg = state.get("cdg") or {}

        coherence = float(narrative.get("coherence", stability.get("narrative_coherence", 0.7)))
        overall = float(stability.get("overall_stability_score", 0.75))

        report.identity_basin_depth = round(min(1.0, coherence * 0.6 + overall * 0.4), 4)
        report.reality_coupling_score = round(
            max(
                report.reality_coupling_score,
                float((cdg.get("last_decision") or {}).get("rcs", 0.0) or 0.0),
            ),
            4,
        )

        trajectory = cdg.get("trajectory") or {}
        drift_mean = float(trajectory.get("drift_mean", 0.1) or 0.1)
        report.drift_index = {
            "identity_drift": round(1.0 - coherence, 4),
            "reality_drift": round(drift_mean, 4),
            "narrative_drift": round(report.narrative_dominance, 4),
        }
        return report

    def _infer_attractors(
        self,
        attribution: Dict[str, float],
        runtime_state: Optional[Dict[str, Any]],
    ) -> List[str]:
        ranked = sorted(attribution.items(), key=lambda x: x[1], reverse=True)
        attractors: list[str] = []

        mapping = {
            "reality_driven": "现实耦合校正",
            "user_driven": "关系维护倾向",
            "narrative_driven": "高一致性人格",
            "self_reinforcing": "身份连续维护",
        }
        for src, weight in ranked[:3]:
            if weight >= 0.18 and src in mapping:
                attractors.append(mapping[src])

        if runtime_state:
            goals = (
                runtime_state.get("narrative", {}).get("summary", "")
                or runtime_state.get("cognitive_state", {}).get("goal_focus", "")
            )
            if "稳定" in str(goals) or "stable" in str(goals).lower():
                if "稳定型助手" not in attractors:
                    attractors.insert(0, "稳定型助手")

        if not attractors:
            attractors = list(self.DEFAULT_ATTRACTORS[:2])
        return attractors[:5]
