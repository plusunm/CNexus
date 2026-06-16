"""Phase 1 — caller-aware policy overlay (no score, no runtime mutation)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from core.control_plane.types import DispatchContext, RouteKind


class DecisionType(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    SIGNAL_REJECT = "signal_reject"


@dataclass(frozen=True)
class Decision:
    type: DecisionType
    reason: str
    route_kind: str
    registry_entry: str
    caller: str
    channel: str

    def blocks_when_hard_gate(self) -> bool:
        return self.type is DecisionType.SIGNAL_REJECT


class DecisionEngine:
    """Non-invasive overlay: observability + soft reject signals; no execution mutation."""

    def decide(
        self,
        ctx: "DispatchContext",
        *,
        registry_entry: str,
        spec: Dict[str, Any],
    ) -> Decision:
        route_kind = ctx.kind.value
        base = dict(
            route_kind=route_kind,
            registry_entry=registry_entry,
            caller=ctx.caller,
            channel=ctx.channel,
        )

        if ctx.caller == "legacy_api":
            return Decision(type=DecisionType.WARN, reason="LEGACY_CALLER", **base)

        if spec.get("deprecated_for_external"):
            return Decision(type=DecisionType.WARN, reason="DEPRECATED_ENTRY", **base)

        return Decision(type=DecisionType.ALLOW, reason="OK", **base)

    @staticmethod
    def unknown_entry(
        ctx: "DispatchContext",
        *,
        registry_entry: str = "",
    ) -> Decision:
        return Decision(
            type=DecisionType.SIGNAL_REJECT,
            reason="UNKNOWN_ENTRY",
            route_kind=ctx.kind.value,
            registry_entry=registry_entry,
            caller=ctx.caller,
            channel=ctx.channel,
        )
