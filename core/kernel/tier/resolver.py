"""Resolve execution tier from intent shape."""

from __future__ import annotations

from typing import Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from core.kernel.context import ExecutionContext
    from core.kernel.intent import ExecutionIntent

ExecutionTier = Literal["T0", "T1", "T2", "T3"]


def resolve_execution_tier(
    intent: "ExecutionIntent",
    ctx: "ExecutionContext | None" = None,
) -> ExecutionTier:
    if intent.type != "chat":
        return "T3"

    action = intent.payload.get("_action")
    if action in ("prepare", "confirm", "cancel"):
        return "T2"

    if intent.payload.get("fast") is True:
        return "T0"
    if intent.payload.get("use_memory") is False:
        return "T1"
    if intent.payload.get("deep_reasoning") is True:
        return "T3"
    return "T2"
