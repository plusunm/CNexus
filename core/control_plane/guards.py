"""Phase 0: dispatch context tracking and direct-access warnings (no HTTP blocking)."""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from core.runtime.execution_tap import get_execution_tap
from core.runtime.trace_context import get_trace_id, start_trace

logger = logging.getLogger(__name__)

_dispatch_depth: ContextVar[int] = ContextVar("cnexus_dispatch_depth", default=0)


def _auto_trace_direct_enabled() -> bool:
    return os.environ.get("CNEXUS_AUTO_TRACE_DIRECT", "1").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def is_dispatch_active() -> bool:
    return _dispatch_depth.get() > 0


@contextmanager
def dispatch_context() -> Iterator[None]:
    token = _dispatch_depth.set(_dispatch_depth.get() + 1)
    try:
        yield
    finally:
        _dispatch_depth.reset(token)


def warn_direct_runtime_access(operation: str) -> None:
    if is_dispatch_active():
        return
    auto_trace: str | None = None
    if _auto_trace_direct_enabled() and get_trace_id() is None:
        auto_trace = start_trace(f"trace-direct-{operation}-{uuid.uuid4().hex[:8]}")
    effective_trace = get_trace_id() or auto_trace
    get_execution_tap().record(
        event_type=f"direct_{operation}",
        summary=f"direct runtime.{operation}",
        trace_id=effective_trace,
        impact="read",
        payload={"operation": operation, "source": "direct_access"},
        spine_written=False,
    )
    logger.warning(
        "direct runtime.%s bypasses AuthorityDispatcher (Phase 0 observability only)%s",
        operation,
        f"; auto_trace={auto_trace}" if auto_trace else "",
    )
