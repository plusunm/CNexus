"""L3-G0 — L2→L3 leakage probe (interpretation / control boundary monitoring)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.authority_router import AuthorityRouter
from core.governance.l3.types import AuthorityLevel


class LeakageProbe:
    """监测 L2 → L3 的潜在控制泄露（只记录，不执行）。"""

    def __init__(self, router: AuthorityRouter | None = None) -> None:
        self.router = router or AuthorityRouter()
        self.events: list[dict[str, Any]] = []

    def record(self, signal: dict) -> None:
        level = self.router.classify(signal)
        decision = self.router.route(signal)
        self.events.append(
            {
                "signal": signal,
                "level": level,
                "decision": decision,
            }
        )

    def violations(self) -> list[dict[str, Any]]:
        """Boundary violations: governance attempts or rejected routes."""
        out: list[dict[str, Any]] = []
        for event in self.events:
            decision = event["decision"]
            if not decision.allowed or event["level"] == AuthorityLevel.GOVERNANCE_ATTEMPT:
                out.append(
                    {
                        "source": event["signal"].get("source", "unknown"),
                        "type": event["signal"].get("type", "unknown"),
                        "action": decision.action,
                        "reason": decision.reason,
                    }
                )
        return out

    def summary(self) -> dict[str, int]:
        obs = sum(1 for e in self.events if e["level"] == AuthorityLevel.OBSERVATION)
        interp = sum(1 for e in self.events if e["level"] == AuthorityLevel.INTERPRETATION)
        gov = sum(1 for e in self.events if e["level"] == AuthorityLevel.GOVERNANCE_ATTEMPT)
        return {
            "total_signals": len(self.events),
            "observation": obs,
            "interpretation": interp,
            "governance_attempt": gov,
            "violations_detected": len(self.violations()),
        }
