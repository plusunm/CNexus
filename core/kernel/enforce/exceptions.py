"""Kernel enforce violations."""

from __future__ import annotations


class KernelViolation(RuntimeError):
    """Raised when execution attempts to bypass the kernel truth path."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        message = f"KERNEL_VIOLATION:{code}"
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)
