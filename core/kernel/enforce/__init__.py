"""Kernel Enforce Mode — CP-3 reality gate."""

from core.kernel.enforce.context import (
    is_kernel_context,
    kernel_execution_context,
    require_kernel_context,
)
from core.kernel.enforce.exceptions import KernelViolation
from core.kernel.enforce.gate import KernelEnforceGate, get_enforce_gate
from core.kernel.enforce.mode import enforce_mode, execution_via_kernel_required, hard_lock_mode

__all__ = [
    "KernelEnforceGate",
    "KernelViolation",
    "enforce_mode",
    "execution_via_kernel_required",
    "hard_lock_mode",
    "get_enforce_gate",
    "is_kernel_context",
    "kernel_execution_context",
    "require_kernel_context",
]
