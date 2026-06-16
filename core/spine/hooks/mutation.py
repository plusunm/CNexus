"""Memory mutation execution spine hooks."""

from __future__ import annotations

from typing import Any, Optional

from core.spine.emit import emit_memory_mutation
from core.spine.execution_context import resolve_llm_trigger, resolve_recall_trigger


def emit_capture_mutation(
    *,
    memory_id: str,
    role: str,
    layer: str,
    importance: float,
    triggered_by: Optional[str] = None,
) -> None:
    emit_memory_mutation(
        kind="capture",
        summary=f"memory_mutation · capture · {role}/{layer}",
        triggered_by=triggered_by or resolve_recall_trigger() or resolve_llm_trigger(),
        payload={
            "memory_id": memory_id,
            "role": role,
            "layer": layer,
            "importance": importance,
        },
    )


def emit_cdg_mutation(
    *,
    phase: str,
    intent_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    emit_memory_mutation(
        kind="cdg_apply",
        summary=f"memory_mutation · cdg · {phase}",
        triggered_by=triggered_by or resolve_recall_trigger(),
        payload={"phase": phase, "intent_id": intent_id, **(extra or {})},
    )


def emit_ir_mutation(
    *,
    event_count: int,
    capture_count: int,
    triggered_by: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    emit_memory_mutation(
        kind="ir_commit",
        summary=f"memory_mutation · ir · {capture_count} captures",
        triggered_by=triggered_by or resolve_recall_trigger() or resolve_llm_trigger(),
        payload={
            "event_count": event_count,
            "capture_count": capture_count,
            **(extra or {}),
        },
    )
