"""CDG Kernel v1 — shared control-plane types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class CDGInteraction:
    """Normalized interaction envelope for governance."""

    user_input: str
    role: str = "user"
    semantic_claims: List[str] = field(default_factory=list)
    replay_anchor: Optional[str] = None
    replay_ref: Optional[str] = None

    @classmethod
    def from_user_input(
        cls,
        user_input: str,
        *,
        replay_anchor: Optional[str] = None,
        replay_ref: Optional[str] = None,
    ) -> "CDGInteraction":
        claims = _extract_semantic_claims(user_input)
        return cls(
            user_input=user_input,
            semantic_claims=claims,
            replay_anchor=replay_anchor,
            replay_ref=replay_ref,
        )


@dataclass
class DriftSnapshot:
    identity_drift: float = 0.0
    narrative_drift: float = 0.0
    goal_drift: float = 0.0
    reality_drift: float = 0.0

    @property
    def max_drift(self) -> float:
        return max(
            self.identity_drift,
            self.narrative_drift,
            self.goal_drift,
            self.reality_drift,
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "identity_drift": self.identity_drift,
            "narrative_drift": self.narrative_drift,
            "goal_drift": self.goal_drift,
            "reality_drift": self.reality_drift,
            "max_drift": self.max_drift,
        }


@dataclass
class BasinDepth:
    depth: float
    stability: float


@dataclass
class AttractorState:
    basin_depth: BasinDepth
    lock_in_risk: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "basin_depth": self.basin_depth.depth,
            "stability": self.basin_depth.stability,
            "lock_in_risk": self.lock_in_risk,
        }


@dataclass
class GovernanceVerdict:
    allow: bool = True
    reason: str = "approved"
    safe_response: Optional[str] = None
    flags: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def flag(self, name: str) -> None:
        if name not in self.flags:
            self.flags.append(name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allow": self.allow,
            "reason": self.reason,
            "safe_response": self.safe_response,
            "flags": list(self.flags),
            "metrics": dict(self.metrics),
        }


@dataclass
class CDGCycleRecord:
    timestamp: str
    reality_coupling: float
    drift: DriftSnapshot
    attractor: AttractorState
    flags: List[str]
    allow: bool
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "reality_coupling": self.reality_coupling,
            "drift": self.drift.to_dict(),
            "attractor": self.attractor.to_dict(),
            "flags": list(self.flags),
            "allow": self.allow,
            "reason": self.reason,
        }


def _extract_semantic_claims(text: str) -> List[str]:
    """Lightweight factual claim extraction for reality coupling."""
    lower = text.lower()
    claims: List[str] = []
    markers = (
        "事实是",
        "实际上",
        "已经",
        "从未",
        "always",
        "never",
        "confirmed",
        "verified",
    )
    for part in text.replace("。", ".").replace("；", ";").split("."):
        chunk = part.strip()
        if not chunk:
            continue
        if any(m in chunk.lower() for m in markers) or len(chunk) > 40:
            claims.append(chunk[:240])
    if not claims and len(text.strip()) > 12:
        claims.append(text.strip()[:240])
    return claims[:8]


def text_alignment(a: str, b: str) -> float:
    """Token overlap alignment in [0, 1]."""
    if not a or not b:
        return 0.5
    ta = set(a.lower().split())
    tb = set(b.lower().split())
    if not ta or not tb:
        return 0.5
    union = ta | tb
    if not union:
        return 0.5
    return len(ta & tb) / len(union)


def normalized_distance(a: str, b: str) -> float:
    """Distance in [0, 1] derived from alignment."""
    return max(0.0, min(1.0, 1.0 - text_alignment(a, b)))
