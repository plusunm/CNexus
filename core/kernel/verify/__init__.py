"""Kernel Final Verification Protocol — CP-3 single-truth closure audit."""

from __future__ import annotations

from core.kernel.verify.compliance import (
    ComplianceViolationError,
    assert_observability_compliance,
    scan_observe_leaks,
)
from core.kernel.verify.protocol import (
    KERNEL_VERIFY_VERSION,
    KernelFinalVerificationProtocol,
    VerificationReport,
    format_report,
    run_verification,
)

__all__ = [
    "KERNEL_VERIFY_VERSION",
    "ComplianceViolationError",
    "assert_observability_compliance",
    "KernelFinalVerificationProtocol",
    "VerificationReport",
    "format_report",
    "run_verification",
    "scan_observe_leaks",
]
