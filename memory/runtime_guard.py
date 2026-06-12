"""Runtime write guard — all L1 memory mutations must occur under BrainMemoryRuntime."""

from __future__ import annotations

import contextvars
import uuid
from contextlib import contextmanager
from typing import Iterator, Optional

_runtime_write_depth: contextvars.ContextVar[int] = contextvars.ContextVar(
    "cnexus_runtime_write_depth", default=0
)
_runtime_write_token: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "cnexus_runtime_write_token", default=None
)


class RuntimeViolationError(RuntimeError):
    """Raised when memory is written outside BrainMemoryRuntime."""

    def __init__(self, operation: str, hint: str = ""):
        message = (
            f"Memory write blocked: {operation} must go through BrainMemoryRuntime "
            f"(process_interaction / capture / reflect)."
        )
        if hint:
            message = f"{message} {hint}"
        super().__init__(message)
        self.operation = operation


def is_runtime_write_allowed() -> bool:
    return _runtime_write_depth.get() > 0


def current_runtime_token() -> Optional[str]:
    return _runtime_write_token.get()


@contextmanager
def runtime_write_context(*, token: Optional[str] = None) -> Iterator[str]:
    """Enter authorized runtime write scope (used by BrainMemoryRuntime internals)."""
    tok = token or str(uuid.uuid4())
    depth = _runtime_write_depth.get()
    token_var = _runtime_write_token.set(tok)
    depth_var = _runtime_write_depth.set(depth + 1)
    try:
        yield tok
    finally:
        _runtime_write_depth.reset(depth_var)
        _runtime_write_token.reset(token_var)


def assert_runtime_context(operation: str) -> None:
    import os

    if os.environ.get("CNEXUS_BYPASS_RUNTIME_GUARD") == "1":
        return
    if not is_runtime_write_allowed():
        raise RuntimeViolationError(operation)
