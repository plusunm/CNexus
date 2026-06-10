"""
GTBS-L2 semantic interpreter (read-only).

S2 Interpretation ≠ Governance | S4 Divergence ≠ Failure
S6 No Temporal Governance | S7 No Control Leakage
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.governance.l2.language import classify_openness, classify_reality_coupling
from core.governance.l2.report_templates import (
    CONTINUITY_TEMPLATE,
    DIVERGENCE_TEMPLATE,
    ECOLOGY_TEMPLATE,
    EMPTY_SNAPSHOT_NOTE,
    SHAPING_TEMPLATE,
)
from core.governance.l2.temporal.trajectory_synthesizer import TrajectorySynthesizer

if TYPE_CHECKING:
    from core.governance.l2.snapshot import GTBSSnapshot
    from core.governance.l2.temporal.types import L2TemporalWindow

_SOURCE_LABELS = {
    "reality_driven": "现实驱动",
    "user_driven": "用户交互驱动",
    "narrative_driven": "叙事驱动",
    "self_reinforcing": "自强化循环",
    "unknown": "未知",
}


def _risk_float(raw: object) -> float:
    if isinstance(raw, str):
        return {"low": 0.15, "moderate": 0.45, "elevated": 0.70}.get(raw, 0.3)
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.3


class SemanticInterpreter:
    """语义解释引擎（只读）"""

    def __init__(self) -> None:
        self._trajectory = TrajectorySynthesizer()

    def interpret_temporal(self, window: L2TemporalWindow) -> dict[str, str]:
        """
        Temporal narrative synthesis — how the system became what it is.

        S6: no prediction, recommendation, or intervention.
        """
        stories = self._trajectory.synthesize(window)
        return {
            "drift_story": stories["drift_story"],
            "stability_story": stories["stability_story"],
            "pressure_story": stories["pressure_story"],
        }

    def interpret_divergence(self, snapshot: GTBSSnapshot) -> str:
        if snapshot.is_empty:
            return EMPTY_SNAPSHOT_NOTE
        d = float(snapshot.divergence.get("proposal_alignment", 0.5))
        if d > 0.8:
            interp = "系统行为与预期高度一致，结构稳定。（描述性信号，非 runtime fault）"
        elif d > 0.5:
            interp = "存在轻微语义偏移，但仍在可观察范围内。"
        else:
            interp = "检测到显著结构偏移，需关注潜在分叉趋势（epistemic signal only）。"
        return DIVERGENCE_TEMPLATE.format(alignment=d, interpretation=interp)

    def interpret_shaping(self, snapshot: GTBSSnapshot) -> str:
        if snapshot.is_empty:
            return EMPTY_SNAPSHOT_NOTE
        risk = _risk_float(snapshot.shaping.get("self_reinforcing_risk", 0.3))
        primary = _SOURCE_LABELS.get(
            str(snapshot.shaping.get("primary_source", "unknown")),
            str(snapshot.shaping.get("primary_source", "unknown")),
        )
        return SHAPING_TEMPLATE.format(
            primary_source=primary,
            risk_note="高自强化风险" if risk > 0.6 else "正常范围内",
        )

    def interpret_continuity(self, snapshot: GTBSSnapshot) -> str:
        if snapshot.is_empty:
            return EMPTY_SNAPSHOT_NOTE
        r = float(snapshot.continuity.get("reality_coupling", 0.5))
        o = float(snapshot.continuity.get("openness", 0.5))
        return CONTINUITY_TEMPLATE.format(
            reality_state=classify_reality_coupling(r),
            openness_state=classify_openness(o),
            stability_note="稳定" if r > 0.6 and o > 0.4 else "存在漂移风险",
        )

    def interpret_ecology(self, snapshot: GTBSSnapshot) -> str:
        if snapshot.is_empty:
            return EMPTY_SNAPSHOT_NOTE
        health = float(snapshot.ecology.get("ecosystem_health", 0.5))
        return ECOLOGY_TEMPLATE.format(
            attractor_state=snapshot.ecology.get("attractor_state", "unknown"),
            health_summary="健康" if health > 0.6 else "需关注结构集中趋势",
        )
