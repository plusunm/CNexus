"""Dispatch types — RouteKind maps to entry_registry via registry.ROUTE_ENTRY_MAP."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class RouteKind(str, Enum):
    CHAT_SEND = "chat_send"
    CHAT_PREPARE = "chat_prepare"
    CHAT_CONFIRM = "chat_confirm"
    CHAT_CANCEL = "chat_cancel"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    MEMORY_MAINTENANCE = "memory_maintenance"
    CAPTURE_COGNITION = "capture_cognition"
    REFLECT_REVIEW = "reflect_review"
    REFLECT_DUE_REVIEWS = "reflect_due_reviews"
    GOVERNANCE_VALIDATE = "governance_validate"
    OBSERVE_READ = "observe_read"
    IR_EXECUTE = "ir_execute"
    IR_COMPILE = "ir_compile"
    GOVERNANCE_CYCLE = "governance_cycle"
    WS_CHAT = "ws_chat"


@dataclass
class DispatchContext:
    kind: RouteKind
    payload: Dict[str, Any] = field(default_factory=dict)
    caller: str = "http"
    channel: str = "brain-memory-ui"
    trace_id: Optional[str] = None


def build_dispatch_context(
    kind: RouteKind,
    payload: Optional[Dict[str, Any]] = None,
    *,
    caller: str = "http",
    channel: str = "brain-memory-ui",
    trace_id: Optional[str] = None,
) -> DispatchContext:
    return DispatchContext(
        kind=kind,
        payload=dict(payload or {}),
        caller=caller,
        channel=channel,
        trace_id=trace_id,
    )
