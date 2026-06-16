"""Capability registry — intent type → handler name (replaces scattered entry points)."""

from __future__ import annotations

from typing import Callable, Dict

from core.kernel.intent import IntentType

Handler = Callable[..., object]

_REGISTRY: Dict[IntentType, str] = {
    "chat": "runtime.process_interaction",
    "recall": "runtime.recall",
    "capture": "runtime.capture",
    "control": "runtime.run_governance_cycle",
    "cdg_apply": "runtime.run_governance_cycle",
    "ir_exec": "ir_kernel.compile_and_execute",
    "system": "ir_kernel.compile_graph",
    "memory_maintenance": "runtime.run_memory_maintenance",
    "capture_cognition": "runtime.process_capture_cognition",
    "reflect_review": "runtime.trait_based_reflection",
    "reflect_due_reviews": "runtime.reflection_pipeline.run_due_reviews",
    "governance_validate": "runtime.run_validation_suite",
    "observe": "kernel.observe",
}


def register_intent(intent_type: IntentType, handler_path: str) -> None:
    _REGISTRY[intent_type] = handler_path


def resolve_handler(intent_type: IntentType) -> str:
    if intent_type not in _REGISTRY:
        raise KeyError(f"unregistered intent type: {intent_type}")
    return _REGISTRY[intent_type]


def all_capabilities() -> dict[str, str]:
    return dict(_REGISTRY)
