"""Control-plane rejection semantics."""

from __future__ import annotations

from core.control_plane.decision_engine import Decision


class ControlDecisionRejected(Exception):
    """Raised when CONTROL_PLANE_HARD_GATE blocks a signaled reject."""

    def __init__(self, decision: Decision):
        self.decision = decision
        super().__init__(decision.reason)
