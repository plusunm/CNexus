"""
Phase A — unified landscape report orchestrator (instrumentation-only).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from core.governance.continuity.trajectory_report import TrajectoryObservabilityEngine
from core.governance.gtbs.divergence_analysis import DivergenceAnalyzer
from core.governance.reconstruction.drift_audit import ReconstructionDriftAuditor
from core.governance.reconstruction.frozen_anchor import FrozenEpisodicAnchorRegistry
from core.governance.shaping.attribution import ShapingAttributor


@dataclass
class PhaseALandscapeReport:
    """Full Phase A observability bundle."""

    divergence: Dict[str, Any]
    shaping: Dict[str, Any]
    reconstruction: Dict[str, Any]
    trajectory: Dict[str, Any]
    anchors_recorded: int = 0
    north_star: str = "Reality-Governed Continuity"

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": "Phase A — Divergence Landscape Mapping",
            "instrumentation_only": True,
            "no_enforcement": True,
            "north_star": self.north_star,
            "divergence_landscape": self.divergence,
            "shaping_attribution": self.shaping,
            "reconstruction_drift": self.reconstruction,
            "current_self_trajectory": self.trajectory,
            "anchors_recorded_this_run": self.anchors_recorded,
        }


class PhaseALandscapeMapper:
    """
    Orchestrate Phase A analytics.

    Invariants: no enforcement, no audit merge, no runtime mutation.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)

    def generate(
        self,
        *,
        runtime_state: Optional[Dict[str, Any]] = None,
        record_anchors: bool = True,
    ) -> PhaseALandscapeReport:
        analyzer = DivergenceAnalyzer(self.base_dir)
        shadow_rows = analyzer.load()

        anchors_recorded = 0
        if record_anchors and shadow_rows:
            registry = FrozenEpisodicAnchorRegistry(self.base_dir)
            anchors_recorded = len(registry.scan_and_record(shadow_rows))

        divergence = analyzer.analyze(shadow_rows).to_dict()
        shaping = ShapingAttributor().analyze(shadow_rows).to_dict()
        reconstruction = ReconstructionDriftAuditor(self.base_dir).analyze(shadow_rows).to_dict()
        trajectory = TrajectoryObservabilityEngine(str(self.base_dir)).build(runtime_state).to_dict()

        return PhaseALandscapeReport(
            divergence=divergence,
            shaping=shaping,
            reconstruction=reconstruction,
            trajectory=trajectory,
            anchors_recorded=anchors_recorded,
        )
