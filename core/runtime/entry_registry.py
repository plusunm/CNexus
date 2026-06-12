"""Runtime entry capability and governance matrix."""

from __future__ import annotations

from typing import Any, Dict, Literal

EntryName = Literal[
    "process_interaction",
    "capture",
    "trait_based_reflection",
    "v1_capture",
    "memory_capture",
    "legacy_endpoints_capture",
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
}


def get_entry_spec(name: str) -> Dict[str, Any]:
    return dict(RUNTIME_ENTRY_MATRIX.get(name, {}))


def list_external_recommended() -> list[str]:
    return [k for k, v in RUNTIME_ENTRY_MATRIX.items() if v.get("recommended") is True]
