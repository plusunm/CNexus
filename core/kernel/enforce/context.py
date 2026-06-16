"""Kernel execution context — marks truth-generation scope."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator, Optional

_kernel_depth: ContextVar[int] = ContextVar("cnexus_kernel_depth", default=0)
_kernel_source: ContextVar[Optional[str]] = ContextVar("cnexus_kernel_source", default=None)


def is_kernel_context() -> bool:
    return _kernel_depth.get() > 0


def kernel_source() -> Optional[str]:
    return _kernel_source.get()


def require_kernel_context(operation: str) -> None:
    from core.kernel.enforce.exceptions import KernelViolation
    from core.kernel.enforce.mode import enforce_mode

    if enforce_mode() and not is_kernel_context():
        raise KernelViolation("NON_KERNEL_EXECUTION_BLOCKED", operation)


@contextmanager
def kernel_execution_context(*, source: str = "kernel") -> Iterator[None]:
    depth_token: Token = _kernel_depth.set(_kernel_depth.get() + 1)
    source_token: Token = _kernel_source.set(source)
    try:
        yield
    finally:
        _kernel_depth.reset(depth_token)
        _kernel_source.reset(source_token)
