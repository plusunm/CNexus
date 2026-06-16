"""In-trace execution anchors for semantic causal linking (CP-2.5 Step 2)."""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

_last_recall_event_id: ContextVar[Optional[str]] = ContextVar(
    "cnexus_last_recall_event_id",
    default=None,
)
_last_llm_event_id: ContextVar[Optional[str]] = ContextVar(
    "cnexus_last_llm_event_id",
    default=None,
)
_last_dispatch_event_id: ContextVar[Optional[str]] = ContextVar(
    "cnexus_last_dispatch_event_id",
    default=None,
)
_last_chat_event_id: ContextVar[Optional[str]] = ContextVar(
    "cnexus_last_chat_event_id",
    default=None,
)
_last_capture_event_id: ContextVar[Optional[str]] = ContextVar(
    "cnexus_last_capture_event_id",
    default=None,
)


def note_execution_event(event_type: str, event_id: str) -> None:
    if event_type == "recall":
        _last_recall_event_id.set(event_id)
    elif event_type == "llm_call":
        _last_llm_event_id.set(event_id)
    elif event_type == "dispatch":
        _last_dispatch_event_id.set(event_id)
    elif event_type == "chat":
        _last_chat_event_id.set(event_id)
    elif event_type in ("capture", "memory_mutation"):
        _last_capture_event_id.set(event_id)


def resolve_recall_trigger() -> Optional[str]:
    return _last_recall_event_id.get()


def resolve_llm_trigger() -> Optional[str]:
    return _last_llm_event_id.get()


def resolve_dispatch_trigger() -> Optional[str]:
    return _last_dispatch_event_id.get()


def resolve_chat_trigger() -> Optional[str]:
    return _last_chat_event_id.get()


def resolve_capture_trigger() -> Optional[str]:
    return _last_capture_event_id.get()
