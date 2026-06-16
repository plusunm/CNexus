"""IR commit → WriteIntent (explicit write, shadow emit)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.governance.gtbs.types import GovernanceProposal, JustificationSource, OperationType, StateDelta
from core.governance.gtbs.write_intent import (
    MutabilityLevel,
    WriteIntent,
    WriteIntentKind,
)
from core.governance.gtbs.write_intent_bus import WriteIntentBus, shadow_emit_enabled

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def emit_ir_commit_intent(
    bus: WriteIntentBus,
    *,
    events: List[Any],
    template: Optional[str] = None,
    commit: bool = True,
) -> WriteIntent:
    capture_events = [e for e in events if getattr(e, "kind", None) == "capture"]
    proposal = GovernanceProposal(
        operation_type=OperationType.INGEST,
        deltas=[
            StateDelta(
                target_store="storage",  # type: ignore[arg-type]
                payload={
                    "event_count": len(events),
                    "capture_count": len(capture_events),
                    "template": template,
                    "commit": commit,
                    "roles": [getattr(e, "role", "") for e in capture_events[:5]],
                },
                description="ir_kernel apply_commits",
            )
        ],
        justification={
            "source": JustificationSource.RUNTIME_SIGNAL.value,
            "operation": "ir_commit",
        },
        source="ir_kernel",
        metadata={
            "write_intent_kind": WriteIntentKind.IR_COMMIT.value,
            "mutability": MutabilityLevel.EXPLICIT.value,
        },
    )
    intent = WriteIntent(
        kind=WriteIntentKind.IR_COMMIT,
        mutability=MutabilityLevel.EXPLICIT,
        proposal=proposal,
    )
    bus.emit(intent)
    return intent


def maybe_emit_ir_commit_shadow(
    runtime: "BrainMemoryRuntime",
    *,
    events: List[Any],
    template: Optional[str] = None,
    commit: bool = True,
) -> Optional[str]:
    if not shadow_emit_enabled(config=getattr(runtime, "config", None)):
        return None
    get_bus = getattr(runtime, "_get_write_intent_bus", None)
    if not callable(get_bus):
        return None
    if not events:
        return None
    intent = emit_ir_commit_intent(
        get_bus(),
        events=events,
        template=template,
        commit=commit,
    )
    return intent.intent_id
