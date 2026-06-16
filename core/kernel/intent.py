"""Execution intent — canonical request shape for kernel.execute()."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

from core.control_plane.types import DispatchContext, RouteKind

IntentType = Literal[
    "chat",
    "recall",
    "capture",
    "control",
    "cdg_apply",
    "ir_exec",
    "system",
    "memory_maintenance",
    "capture_cognition",
    "reflect_review",
    "reflect_due_reviews",
    "governance_validate",
    "observe",
]

_ROUTE_TO_INTENT: dict[RouteKind, IntentType] = {
    RouteKind.CHAT_SEND: "chat",
    RouteKind.WS_CHAT: "chat",
    RouteKind.CHAT_PREPARE: "chat",
    RouteKind.CHAT_CONFIRM: "chat",
    RouteKind.CHAT_CANCEL: "chat",
    RouteKind.MEMORY_READ: "recall",
    RouteKind.MEMORY_WRITE: "capture",
    RouteKind.MEMORY_MAINTENANCE: "memory_maintenance",
    RouteKind.CAPTURE_COGNITION: "capture_cognition",
    RouteKind.REFLECT_REVIEW: "reflect_review",
    RouteKind.REFLECT_DUE_REVIEWS: "reflect_due_reviews",
    RouteKind.GOVERNANCE_VALIDATE: "governance_validate",
    RouteKind.OBSERVE_READ: "observe",
    RouteKind.GOVERNANCE_CYCLE: "cdg_apply",
    RouteKind.IR_EXECUTE: "ir_exec",
    RouteKind.IR_COMPILE: "system",
}

_CHAT_ACTIONS: dict[RouteKind, str] = {
    RouteKind.CHAT_PREPARE: "prepare",
    RouteKind.CHAT_CONFIRM: "confirm",
    RouteKind.CHAT_CANCEL: "cancel",
}


@dataclass
class ExecutionIntent:
    type: IntentType
    payload: Dict[str, Any]
    trace_id: Optional[str] = None
    source: str = "ui"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "payload": self.payload,
            "trace_id": self.trace_id,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionIntent":
        return cls(
            type=data["type"],
            payload=dict(data.get("payload") or {}),
            trace_id=data.get("trace_id"),
            source=str(data.get("source") or "ui"),
            metadata=dict(data.get("metadata") or {}),
        )


def dispatch_context_to_intent(ctx: DispatchContext) -> ExecutionIntent:
    """Map AuthorityDispatcher context → kernel intent (migration bridge)."""
    intent_type = _ROUTE_TO_INTENT.get(ctx.kind)
    if intent_type is None:
        raise ValueError(f"unsupported dispatch kind for kernel: {ctx.kind}")

    payload = dict(ctx.payload)
    metadata: dict[str, Any] = {
        "dispatch_kind": ctx.kind.value,
        "caller": ctx.caller,
        "channel": ctx.channel,
    }

    action = _CHAT_ACTIONS.get(ctx.kind)
    if action:
        payload["_action"] = action
    if ctx.kind == RouteKind.IR_COMPILE:
        payload["_action"] = "compile"
    if ctx.kind == RouteKind.OBSERVE_READ:
        payload.setdefault("_observe_kind", payload.get("kind") or "unknown")

    return ExecutionIntent(
        type=intent_type,
        payload=payload,
        trace_id=ctx.trace_id,
        source=ctx.caller,
        metadata=metadata,
    )
