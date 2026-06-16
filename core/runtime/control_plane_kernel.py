"""Non-Hang Control Plane Kernel — survival contract (Fix Contract + Boot v3 + Isolation v1).

Ready/health handlers must only depend on symbols exported here and boot_protocol
flags — never on BrainMemoryRuntime construction, cognitive imports, or sync IO.

@see docs/CNEXUS_SYSTEM_CONVERGENCE.md
@see core/runtime/control_plane_isolation.py
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from core.runtime.boot_protocol import (
    BootPhase,
    boot_status,
    evaluate_system_ready,
    get_boot_phase,
    is_runtime_warming,
)
from core.runtime.control_plane_isolation import isolation_enabled, zero_dep_ready_payload

# Injectable runtime pointer — set by brain-memory-ui/api/deps after warm thread.
_runtime_peek: Optional[Callable[[], Any]] = None


def configure_runtime_peek(fn: Callable[[], Any]) -> None:
    """Wire peek_runtime from deps at API startup."""
    global _runtime_peek
    _runtime_peek = fn


def peek_runtime_pointer() -> Any:
    if _runtime_peek is None:
        return None
    return _runtime_peek()


def get_boot_state() -> BootPhase:
    return get_boot_phase()


def control_plane_alive() -> bool:
    return boot_status().get("control_plane_alive", True)


def build_ready_snapshot(
    *,
    app_started: bool,
    token_valid: bool = True,
    license_valid: bool = True,
    memory_ok: bool = True,
) -> dict[str, Any]:
    """IO-free ready payload inputs — safe on event loop."""
    if isolation_enabled():
        return zero_dep_ready_payload(
            app_started=app_started,
            runtime_present=peek_runtime_pointer() is not None,
            token_valid=token_valid,
            license_valid=license_valid,
        )

    runtime = peek_runtime_pointer()
    status = evaluate_system_ready(
        app_started=app_started,
        runtime_present=runtime is not None,
        runtime_warming=is_runtime_warming(),
        memory_ok=memory_ok,
        token_valid=token_valid,
        license_valid=license_valid,
    )
    return {
        "status": status,
        "boot_phase": get_boot_phase().value,
        "runtime_pointer": runtime is not None,
        "control_plane_alive": control_plane_alive(),
        "boot": boot_status(),
    }
