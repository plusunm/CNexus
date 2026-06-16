"""Map spine events → execution phases."""

from __future__ import annotations

from typing import Any


def classify_event_phase(event: dict[str, Any]) -> str:
    """GTBS / runtime spine event → execution phase."""
    etype = str(event.get("event_type") or "")

    if etype in ("dispatch", "write_intent", "chat"):
        return "trigger"

    if etype == "control" or event.get("decision"):
        return "control"

    if etype in ("recall", "llm_call", "ir"):
        return "execution"

    if etype in (
        "capture",
        "memory_mutation",
        "cdg",
        "write",
        "mutation",
    ):
        return "mutation"

    if etype in ("state", "state_patch", "state_diff"):
        return "state"

    if etype == "feedback":
        return "feedback"

    return "execution"


def semantic_edge_to_execution_kind(relation: str) -> str:
    mapping = {
        "triggered_by": "triggers",
        "control_flow": "controls",
        "temporal": "executes",
    }
    return mapping.get(relation, "executes")
