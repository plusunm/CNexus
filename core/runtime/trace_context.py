"""CP-2 trace binding — ContextVar propagated across dispatch / GTBS / spine."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator, Optional

from core.runtime.trace_id import coerce_trace_id, generate_trace_id

_current_trace_id: ContextVar[Optional[str]] = ContextVar("cnexus_trace_id", default=None)


def start_trace(trace_id: Optional[str] = None) -> str:
    tid = coerce_trace_id(trace_id)
    _current_trace_id.set(tid)
    return tid


def get_trace_id() -> Optional[str]:
    return _current_trace_id.get()


def require_trace_id() -> str:
    tid = get_trace_id()
    if not tid:
        raise RuntimeError("Missing trace context")
    return tid


def reset_trace_context() -> None:
    """Clear ambient trace binding (tests / request boundary cleanup)."""
    _current_trace_id.set(None)


@contextmanager
def trace_scope(trace_id: Optional[str] = None) -> Iterator[str]:
    """Bind trace for dispatch subtree; nested scopes restore on exit."""
    incoming = (trace_id or "").strip() or None
    tid = incoming or get_trace_id() or generate_trace_id()
    token: Token = _current_trace_id.set(tid)
    try:
        yield tid
    finally:
        _current_trace_id.reset(token)


def resolve_trace_id(explicit: Optional[str] = None) -> Optional[str]:
    """Prefer explicit trace, then active context."""
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    return get_trace_id()
