"""Kernel Final Verification Protocol — CP-3 single-truth closure audit."""

from __future__ import annotations

from core.kernel.verify.protocol import (
    KERNEL_VERIFY_VERSION,
    KernelFinalVerificationProtocol,
    VerificationReport,
    run_verification,
)

__all__ = [
    "KERNEL_VERIFY_VERSION",
    "KernelFinalVerificationProtocol",
    "VerificationReport",
    "run_verification",
]
