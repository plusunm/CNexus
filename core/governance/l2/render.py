"""
GTBS-L2 semantic alignment renderer (read-only).

S1 Read-Only | S5 Semantic Non-Actuation — output never feeds CDG/runtime/GTBS.
S6 No Temporal Governance | S7 temporal narrative ≠ policy signal
"""

from __future__ import annotations

from typing import Any

from core.governance.l2.attractor import build_attractor_inference_report
from core.governance.l2.attractor.types import GTBSL2AttractorReport
from core.governance.l2.fusion import build_fusion_report
from core.governance.l2.fusion.types import GTBSL2FusionReport
from core.governance.l2.interpreter import SemanticInterpreter
from core.governance.l2.snapshot import GTBSSnapshot
from core.governance.l2.temporal.trajectory_synthesizer import TrajectorySynthesizer
from core.governance.l2.temporal.types import L2TemporalReport, L2TemporalWindow

L2_VERSION = "L2_v0.1"
L2_TEMPORAL_VERSION = "L2_v0.2"
L2_FUSION_VERSION = "L2_v0.3"
L2_ATTRACTOR_VERSION = "L2_v0.5"


class GTBSL2Renderer:
    """GTBS-L2 语义对齐渲染器（只读）"""

    def __init__(self) -> None:
        self.interpreter = SemanticInterpreter()

    def render(self, snapshot: GTBSSnapshot) -> dict[str, Any]:
        if not isinstance(snapshot, GTBSSnapshot):
            raise TypeError("snapshot 必须为 GTBSSnapshot 类型")

        return {
            "timestamp": snapshot.timestamp,
            "narrative_version": L2_VERSION,
            "summaries": {
                "divergence": self.interpreter.interpret_divergence(snapshot),
                "shaping": self.interpreter.interpret_shaping(snapshot),
                "continuity": self.interpreter.interpret_continuity(snapshot),
                "ecology": self.interpreter.interpret_ecology(snapshot),
            },
            "raw_metrics": {
                "divergence": snapshot.divergence,
                "shaping": snapshot.shaping,
                "continuity": snapshot.continuity,
                "ecology": snapshot.ecology,
            },
            "metadata": {
                "l2_layer": "semantic_alignment",
                "read_only": True,
                "instrumentation_only": True,
                "semantic_non_actuation": True,
            },
        }

    def render_narrative_text(self, snapshot: GTBSSnapshot) -> str:
        """Plain-text bundle for CLI output."""
        out = self.render(snapshot)
        header = f"=== GTBS-L2 Semantic Alignment {L2_VERSION} ==="
        blocks = [header, out["summaries"]["continuity"], out["summaries"]["divergence"]]
        blocks.extend([out["summaries"]["shaping"], out["summaries"]["ecology"]])
        blocks.append(
            "(instrumentation_only=true; read_only=true; "
            "semantic non-actuation — 不参与 runtime/CDG/GTBS enforcement)"
        )
        return "\n\n".join(blocks)

    def render_temporal(self, window: L2TemporalWindow) -> L2TemporalReport:
        """GTBS-L2 v0.2 temporal report — trajectory consciousness layer (observational only)."""
        if not isinstance(window, L2TemporalWindow):
            raise TypeError("window 必须为 L2TemporalWindow 类型")

        synthesizer = TrajectorySynthesizer()
        temporal_narratives = self.interpreter.interpret_temporal(window)
        trends = synthesizer.trend_signals(window)

        raw_window = [
            {
                "timestamp": s.timestamp,
                "divergence": s.divergence,
                "shaping": s.shaping,
                "continuity": s.continuity,
                "ecology": s.ecology,
            }
            for s in window.snapshots
        ]

        return L2TemporalReport(
            time_range=f"{window.start_ts} → {window.end_ts} ({window.window_days}d)",
            narrative_version=L2_TEMPORAL_VERSION,
            temporal_summaries={
                "drift": temporal_narratives["drift_story"],
                "stability": temporal_narratives["stability_story"],
                "pressure": temporal_narratives["pressure_story"],
            },
            trend_signals=trends,
            raw_window=raw_window,
            metadata={
                "l2_layer": "semantic_alignment_temporal",
                "read_only": True,
                "instrumentation_only": True,
                "semantic_non_actuation": True,
                "no_temporal_governance": True,
                "snapshot_count": window.snapshot_count,
                "aggregated": window.aggregated,
            },
        )

    def render_temporal_text(self, window: L2TemporalWindow) -> str:
        report = self.render_temporal(window)
        blocks = [
            f"=== GTBS-L2 v0.2 Temporal Report ===",
            f"Time range: {report.time_range}",
            "",
            "--- Drift Narrative ---",
            report.temporal_summaries["drift"],
            "",
            "--- Stability Narrative ---",
            report.temporal_summaries["stability"],
            "",
            "--- Pressure Narrative ---",
            report.temporal_summaries["pressure"],
            "",
            "(S6/S7: pure observational cognition — not a decision system)",
        ]
        return "\n".join(blocks)

    def render_fusion(self, base_dir: str, window_days: int = 7) -> GTBSL2FusionReport:
        """GTBS-L2 v0.3 cross-stream fusion report (field cognition; read-only)."""
        report = build_fusion_report(base_dir, window_days=window_days)
        report.narrative_version = L2_FUSION_VERSION
        return report

    def render_fusion_text(self, base_dir: str, window_days: int = 7) -> str:
        report = self.render_fusion(base_dir, window_days=window_days)
        blocks = [
            "=== GTBS-L2 v0.3 Cross-Stream Fusion Report ===",
            f"Time range: {report.time_range}",
            "",
            "--- Systemic Drift Convergence ---",
            report.fusion_summaries.get("drift_convergence", ""),
            "",
            "--- Coupled Stability ---",
            report.fusion_summaries.get("coupled_stability", ""),
            "",
            "--- Meta-Consistency ---",
            report.fusion_summaries.get("meta_consistency", ""),
            "",
            f"Coupling matrix: {report.coupling_matrix}",
            f"Risk surface: {report.risk_surface}",
            "",
            "(S8/S9/S10: fusion ≠ governance; coupling ≠ causation; observational closure only)",
        ]
        return "\n".join(blocks)

    def render_attractor(self, base_dir: str, window_days: int = 7) -> GTBSL2AttractorReport:
        """GTBS-L2.5 latent attractor inference report (structural inference; read-only)."""
        report = build_attractor_inference_report(base_dir, window_days=window_days)
        report.narrative_version = L2_ATTRACTOR_VERSION
        return report

    def render_attractor_text(self, base_dir: str, window_days: int = 7) -> str:
        report = self.render_attractor(base_dir, window_days=window_days)
        blocks = [
            "=== GTBS-L2.5 Latent Attractor Inference Report ===",
            f"Time range: {report.time_range}",
            f"Field regime: {report.field_regime}",
            f"Global entropy: {report.global_entropy:.2f}",
            "",
            "--- Dominant Attractors ---",
        ]
        for att in report.dominant_attractors:
            blocks.append(
                f"- {att.get('id')}: {att.get('type')} "
                f"(strength={att.get('strength')}, stability={att.get('stability_class')})"
            )
        blocks.extend(
            [
                "",
                "--- Topology ---",
                str(report.topology),
                "",
                "--- Risk Surface ---",
                str(report.risk_surface),
                "",
                "--- Interpretation ---",
                report.interpretation,
                "",
                "(S11/S12: attractor field = structure description; NOT action recommendation)",
            ]
        )
        return "\n".join(blocks)
