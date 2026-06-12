"""
L3-G0 — governance boundary types (descriptive only).

S13 No Control Directness | S14 No Semantic Authority Upgrade
S15 Constraint Non-Executability | S16 No Attractor Control
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class AuthorityLevel(Enum):
    OBSERVATION = auto()
    INTERPRETATION = auto()
    GOVERNANCE_ATTEMPT = auto()


@dataclass(frozen=True)
class Boundary:
    name: str
    scope: str
    description: str
    immutable: bool = True


@dataclass(frozen=True)
class RoutingDecision:
    authority_level: AuthorityLevel
    allowed: bool
    action: str  # allow | downgrade | reject
    reason: str


@dataclass
class L3G0ReportPayload:
    summary: dict[str, Any]
    boundaries: list[dict[str, Any]] = field(default_factory=list)
    violations: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report": "L3-G0 Boundary / Authority Probe Report",
            "summary": self.summary,
            "boundaries": self.boundaries,
            "violations": self.violations,
            "metadata": self.metadata,
        }
