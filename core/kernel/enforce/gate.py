"""Kernel Enforce Gate — reality validation on execute."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, TYPE_CHECKING

from core.kernel.enforce.context import kernel_execution_context
from core.kernel.enforce.exceptions import KernelViolation
from core.kernel.enforce.mode import enforce_mode, hard_lock_mode

if TYPE_CHECKING:
    from core.kernel.intent import ExecutionIntent
    from core.kernel.record import ExecutionRecord


class KernelEnforceGate:
    """Validates that execution only occurs through kernel truth path."""

    @contextmanager
    def execution_scope(self, intent: "ExecutionIntent") -> Iterator[None]:
        with kernel_execution_context(source=intent.source):
            if enforce_mode():
                self._before_execute(intent)
            try:
                yield
            finally:
                if enforce_mode():
                    self._after_scope()

    def validate_record(self, record: "ExecutionRecord") -> None:
        if not enforce_mode():
            return
        if not record.trace_id:
            raise KernelViolation("INVALID_RECORD", "missing trace_id")
        if not record.intent_type:
            raise KernelViolation("INVALID_RECORD", "missing intent_type")
        from core.kernel.kernel import graph_enabled

        tier = (
            (record.derivation or {}).get("execution_tier")
            or (record.audit or {}).get("execution_tier")
            or (record.audit_log or {}).get("execution_tier")
        )
        if tier in ("T0", "T1", "T2"):
            return
        if (record.derivation or {}).get("lazy"):
            return
        if graph_enabled() and record.graph is None:
            raise KernelViolation("MISSING_GRAPH_TRUTH", "graph-enabled but record.graph is empty")

    def block_legacy_route(self, route_name: str) -> None:
        if enforce_mode() or hard_lock_mode():
            raise KernelViolation("NON_KERNEL_EXECUTION_BLOCKED", route_name)

    def block_bypass(self) -> None:
        if enforce_mode() or hard_lock_mode():
            raise KernelViolation("KERNEL_BYPASS_FORBIDDEN")

    def _before_execute(self, intent: "ExecutionIntent") -> None:
        if not intent.type:
            raise KernelViolation("INVALID_INTENT", "missing intent type")

    def _after_scope(self) -> None:
        return


_gate: KernelEnforceGate | None = None


def get_enforce_gate() -> KernelEnforceGate:
    global _gate
    if _gate is None:
        _gate = KernelEnforceGate()
    return _gate
