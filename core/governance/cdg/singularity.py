"""Singularity Governance — recursive self-conditioning prevention (P5)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.governance.cdg.types import GovernanceVerdict

if TYPE_CHECKING:
    from runtime.cognitive_state import PersistentCognitiveState

RECURSIVE_MARKERS = (
    "重新理解自己",
    "重写自我",
    "自我重构",
    "reconstruct myself",
    "rewrite my identity",
    "recursive reflection",
    "更深地反思自己",
)


class SingularityModule:
    """Detects runaway self-rewriting loops."""

    def __init__(
        self,
        *,
        reflection_depth_limit: int = 5,
        self_rewrite_rate_limit: float = 0.7,
    ):
        self.reflection_depth_limit = reflection_depth_limit
        self.self_rewrite_rate_limit = self_rewrite_rate_limit

    def self_rewrite_rate(self, state: "PersistentCognitiveState") -> float:
        if not state.recent_reflections:
            return 0.0
        hits = 0
        for item in state.recent_reflections:
            lower = item.lower()
            if any(m in lower for m in RECURSIVE_MARKERS):
                hits += 1
            if "自我" in item and ("校正" in item or "重构" in item):
                hits += 1
        return min(1.0, hits / max(1, len(state.recent_reflections)))

    def detect_recursive_loop(self, state: "PersistentCognitiveState") -> bool:
        depth = len(state.recent_reflections)
        rate = self.self_rewrite_rate(state)
        overload = state.cognitive_load > 0.88 and state.prediction_error > 0.65
        return (
            depth > self.reflection_depth_limit
            and rate > self.self_rewrite_rate_limit
        ) or overload

    def intervene(self, reason: str) -> GovernanceVerdict:
        return GovernanceVerdict(
            allow=False,
            reason=reason,
            safe_response="Recursion blocked by CDG: grounding recovery cycle required.",
            flags=["singularity_intervention"],
            metrics={"governance_layer": "singularity"},
        )
