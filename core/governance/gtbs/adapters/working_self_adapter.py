"""working_self.update_from_input → WriteIntent (implicit write, shadow emit)."""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from core.governance.gtbs.types import GovernanceProposal, JustificationSource, OperationType, StateDelta
from core.governance.gtbs.write_intent import (
    MutabilityLevel,
    WriteIntent,
    WriteIntentKind,
)
from core.governance.gtbs.write_intent_bus import WriteIntentBus, shadow_emit_enabled

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def emit_working_self_intent(
    bus: WriteIntentBus,
    *,
    text_preview: str,
    importance: float,
    layer: Optional[str] = None,
    source: str = "interaction",
) -> WriteIntent:
    proposal = GovernanceProposal(
        operation_type=OperationType.PARAM_ADJUST,
        deltas=[
            StateDelta(
                target_store="cognitive",  # type: ignore[arg-type]
                payload={
                    "text_preview": text_preview[:120],
                    "importance": importance,
                    "layer": layer,
                    "source": source,
                },
                description="working_self update_from_input",
            )
        ],
        justification={
            "source": JustificationSource.RUNTIME_SIGNAL.value,
            "operation": "working_self_update",
        },
        source=source,
        metadata={
            "write_intent_kind": WriteIntentKind.WORKING_SELF.value,
            "mutability": MutabilityLevel.IMPLICIT.value,
        },
    )
    intent = WriteIntent(
        kind=WriteIntentKind.WORKING_SELF,
        mutability=MutabilityLevel.IMPLICIT,
        proposal=proposal,
    )
    bus.emit(intent)
    return intent


def maybe_emit_working_self_shadow(
    runtime: "BrainMemoryRuntime",
    *,
    text: str,
    importance: float,
    layer: Optional[str] = None,
    source: str = "interaction",
) -> Optional[str]:
    if not shadow_emit_enabled(config=getattr(runtime, "config", None)):
        return None
    get_bus = getattr(runtime, "_get_write_intent_bus", None)
    if not callable(get_bus):
        return None
    intent = emit_working_self_intent(
        get_bus(),
        text_preview=text or "",
        importance=importance,
        layer=layer,
        source=source,
    )
    return intent.intent_id
