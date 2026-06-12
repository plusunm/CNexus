"""L3-G0 — authority router (classify signals; default: governance blocked)."""

from __future__ import annotations

from core.governance.l3.types import AuthorityLevel, RoutingDecision


class AuthorityRouter:
    """分类输入信号为 Observation / Interpretation / Governance Attempt。"""

    def classify(self, signal: dict) -> AuthorityLevel:
        typ = signal.get("type", "observation")
        if typ == "observation":
            return AuthorityLevel.OBSERVATION
        if typ == "interpretation":
            return AuthorityLevel.INTERPRETATION
        if typ == "governance_attempt":
            return AuthorityLevel.GOVERNANCE_ATTEMPT
        return AuthorityLevel.OBSERVATION

    def route(self, signal: dict) -> RoutingDecision:
        """
        Route signal to allowed layer. S13/S14: governance attempts rejected by default.
        """
        level = self.classify(signal)
        if level == AuthorityLevel.GOVERNANCE_ATTEMPT:
            return RoutingDecision(
                authority_level=level,
                allowed=False,
                action="reject",
                reason="S13: L3 cannot directly modify runtime; governance blocked by default",
            )
        if level == AuthorityLevel.INTERPRETATION:
            return RoutingDecision(
                authority_level=level,
                allowed=True,
                action="allow",
                reason="S14: interpretation permitted; cannot upgrade to governance",
            )
        return RoutingDecision(
            authority_level=level,
            allowed=True,
            action="allow",
            reason="observation-only path",
        )
