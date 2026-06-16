"""Auto-wrap policy — which runtime methods route through kernel."""

from __future__ import annotations

from typing import Any, Dict, FrozenSet

KERNEL_INTERNAL = "_kernel_internal"
BYPASS_KERNEL = "_bypass_kernel"

# Execution / mutation entry points (reads and properties are passthrough).
INTERCEPTED_METHODS: FrozenSet[str] = frozenset(
    {
        "process_interaction",
        "prepare_chat_turn",
        "confirm_prepared_chat_turn",
        "cancel_prepared_chat_turn",
        "recall",
        "capture",
        "run_governance_cycle",
        "trait_based_reflection",
        "process_capture_cognition",
        "run_memory_maintenance",
        "maintain_memory",
        "run_validation_suite",
        # Dispatcher-style aliases (if present on runtime or forwarded)
        "chat_send",
        "cdg_ingest",
        "cdg_apply",
        "ir_execute",
        "control",
    }
)


def should_intercept(method_name: str) -> bool:
    return method_name in INTERCEPTED_METHODS


def strip_kernel_flags(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = dict(kwargs)
    cleaned.pop(KERNEL_INTERNAL, None)
    cleaned.pop(BYPASS_KERNEL, None)
    return cleaned
