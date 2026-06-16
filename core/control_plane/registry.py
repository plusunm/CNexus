"""Route → entry_registry mapping and enforcement (Phase 0: warn on deprecated, do not block)."""

from __future__ import annotations

from typing import Any, Dict

from core.runtime.entry_registry import get_entry_spec


class EntryNotRegisteredError(KeyError):
    """HTTP/route kind has no entry_registry mapping."""


ROUTE_ENTRY_MAP: Dict[str, str] = {
    "chat_send": "process_interaction",
    "chat_prepare": "chat_prepare",
    "chat_confirm": "chat_confirm",
    "chat_cancel": "chat_cancel",
    "memory_read": "memory_recall",
    "memory_write": "memory_capture",
    "memory_maintenance": "memory_maintenance",
    "capture_cognition": "capture_cognition",
    "reflect_review": "trait_based_reflection",
    "reflect_due_reviews": "reflect_due_reviews",
    "governance_validate": "governance_validate",
    "observe_read": "observe_read",
    "ir_execute": "ir_execute",
    "ir_compile": "ir_compile",
    "governance_cycle": "governance_cycle",
    "ws_chat": "process_interaction",
}


def resolve_registry_entry(route_kind: str) -> str:
    registry_name = ROUTE_ENTRY_MAP.get(route_kind)
    if not registry_name:
        raise EntryNotRegisteredError(f"unmapped route kind: {route_kind}")
    return registry_name


def enforce_route_entry(route_kind: str) -> Dict[str, Any]:
    registry_name = resolve_registry_entry(route_kind)
    spec = get_entry_spec(registry_name)
    if not spec:
        raise EntryNotRegisteredError(f"entry not in RUNTIME_ENTRY_MATRIX: {registry_name}")
    return spec
