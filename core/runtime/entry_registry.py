"""Runtime entry capability and governance matrix."""

from __future__ import annotations

from typing import Any, Dict, Literal

EntryName = Literal[
    "process_interaction",
    "capture",
    "trait_based_reflection",
    "reflect_due_reviews",
    "memory_maintenance",
    "capture_cognition",
    "governance_validate",
    "observe_read",
    "v1_capture",
    "memory_capture",
    "legacy_endpoints_capture",
    "memory_recall",
    "ir_execute",
    "ir_compile",
    "governance_cycle",
    "chat_prepare",
    "chat_confirm",
    "chat_cancel",
]

RUNTIME_ENTRY_MATRIX: Dict[str, Dict[str, Any]] = {
    "process_interaction": {
        "full_cognitive_loop": True,
        "write_gate": True,
        "deliberation_pre_output": True,
        "cdg_post_state": True,
        "reflection": True,
        "values_check": True,
        "assistant_capture": True,
        "recommended": True,
    },
    "capture": {
        "full_cognitive_loop": False,
        "write_gate": True,
        "deliberation_pre_output": False,
        "cdg_post_state": False,
        "reflection": False,
        "values_check": False,
        "assistant_capture": False,
        "recommended": "internal_only",
        "note": "Use via runtime only; prefer process_interaction for user-facing writes",
    },
    "trait_based_reflection": {
        "full_cognitive_loop": False,
        "write_gate": True,
        "deliberation_pre_output": False,
        "cdg_post_state": "optional",
        "reflection": True,
        "values_check": False,
        "recommended": True,
    },
    "reflect_due_reviews": {
        "full_cognitive_loop": False,
        "write_gate": True,
        "reflection": True,
        "recommended": True,
    },
    "memory_maintenance": {
        "full_cognitive_loop": False,
        "write_gate": True,
        "recommended": True,
    },
    "capture_cognition": {
        "full_cognitive_loop": False,
        "write_gate": True,
        "reflection": True,
        "recommended": True,
    },
    "governance_validate": {
        "full_cognitive_loop": False,
        "read_only": True,
        "recommended": True,
    },
    "observe_read": {
        "full_cognitive_loop": False,
        "read_only": True,
        "mutate_state": False,
        "recommended": True,
    },
    "v1_capture": {
        "full_cognitive_loop": False,
        "http_path": "POST /v1/capture",
        "deprecated_for_external": True,
        "recommended": False,
    },
    "memory_capture": {
        "full_cognitive_loop": False,
        "http_path": "POST /memory/capture",
        "deprecated_for_external": True,
        "recommended": False,
    },
    "memory_recall": {
        "full_cognitive_loop": False,
        "http_path": "GET /memory/recall",
        "mutate_state": False,
        "recommended": True,
    },
    "ir_execute": {
        "full_cognitive_loop": False,
        "http_path": "POST /ir/execute",
        "recommended": True,
    },
    "ir_compile": {
        "full_cognitive_loop": False,
        "http_path": "POST /ir/compile",
        "read_only": True,
        "recommended": True,
    },
    "governance_cycle": {
        "full_cognitive_loop": False,
        "http_path": "POST /governance/cycle",
        "recommended": True,
    },
    "chat_prepare": {
        "full_cognitive_loop": False,
        "http_path": "POST /chat/prepare",
        "mutate_state_on_recall": False,
        "recommended": True,
    },
    "chat_confirm": {
        "full_cognitive_loop": True,
        "http_path": "POST /chat/confirm",
        "recommended": True,
    },
    "chat_cancel": {
        "full_cognitive_loop": False,
        "http_path": "POST /chat/cancel",
        "recommended": True,
    },
}


def get_entry_spec(name: str) -> Dict[str, Any]:
    return dict(RUNTIME_ENTRY_MATRIX.get(name, {}))


def list_external_recommended() -> list[str]:
    return [k for k, v in RUNTIME_ENTRY_MATRIX.items() if v.get("recommended") is True]
