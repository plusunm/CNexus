"""Chat deferred cognition → WriteIntent (explicit write, shadow emit)."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from core.governance.gtbs.types import GovernanceProposal, JustificationSource, OperationType, StateDelta
from core.governance.gtbs.write_intent import (
    MutabilityLevel,
    WriteIntent,
    WriteIntentKind,
)
from core.governance.gtbs.write_intent_bus import WriteIntentBus, shadow_emit_enabled

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def emit_chat_deferred_intent(
    bus: WriteIntentBus,
    *,
    text: str,
    capture_id: Any,
    grounding_event_id: str,
) -> WriteIntent:
    proposal = GovernanceProposal(
        operation_type=OperationType.PARAM_ADJUST,
        deltas=[
            StateDelta(
                target_store=store,  # type: ignore[arg-type]
                payload={
                    "text_preview": (text or "")[:120],
                    "capture_id": str(capture_id) if capture_id else "",
                    "grounding_event_id": grounding_event_id,
                    "phase": "chat_deferred_cognition",
                },
                description=f"chat deferred cognition → {store}",
            )
            for store in ("cognitive", "storage", "personality", "narrative")
        ],
        justification={
            "source": JustificationSource.INTERACTION.value,
            "operation": "chat_deferred",
        },
        source="chat_deferred",
        metadata={
            "write_intent_kind": WriteIntentKind.CHAT_DEFERRED.value,
            "mutability": MutabilityLevel.EXPLICIT.value,
        },
    )
    intent = WriteIntent(
        kind=WriteIntentKind.CHAT_DEFERRED,
        mutability=MutabilityLevel.EXPLICIT,
        proposal=proposal,
    )
    bus.emit(intent)
    return intent


def maybe_emit_chat_deferred_shadow(
    runtime: "BrainMemoryRuntime",
    *,
    text: str,
    capture_id: Any,
    grounding_event_id: str,
) -> Optional[str]:
    if not shadow_emit_enabled(config=getattr(runtime, "config", None)):
        return None
    get_bus = getattr(runtime, "_get_write_intent_bus", None)
    if not callable(get_bus):
        return None
    intent = emit_chat_deferred_intent(
        get_bus(),
        text=text,
        capture_id=capture_id,
        grounding_event_id=grounding_event_id,
    )
    return intent.intent_id
