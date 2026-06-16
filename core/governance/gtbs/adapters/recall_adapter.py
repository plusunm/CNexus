"""Recall mutate_state → WriteIntent (implicit write, shadow emit)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.governance.gtbs.types import JustificationSource, OperationType, StateDelta
from core.governance.gtbs.write_intent import (
    MutabilityLevel,
    WriteIntent,
    WriteIntentKind,
    WriteProvenance,
)
from core.governance.gtbs.write_intent_bus import WriteIntentBus, build_current_provenance, shadow_emit_enabled

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def _recall_target_stores() -> List[str]:
    return ["cognitive", "personality"]


def emit_recall_side_effect_intent(
    bus: WriteIntentBus,
    *,
    query: str,
    top_k: int,
    use_attention: bool,
    activated_count: int,
    top_labels: List[Any],
    provenance: Optional[WriteProvenance] = None,
) -> str:
    labels = [str(label) for label in top_labels if label][:5]
    proposal_source = "recall_pipeline"
    from core.governance.gtbs.types import GovernanceProposal

    proposal = GovernanceProposal(
        operation_type=OperationType.PARAM_ADJUST,
        deltas=[
            StateDelta(
                target_store=store,  # type: ignore[arg-type]
                payload={
                    "query_preview": (query or "")[:120],
                    "top_k": top_k,
                    "use_attention": use_attention,
                    "activated_count": activated_count,
                    "top_labels": labels,
                },
                description=f"recall attention sync → {store}",
            )
            for store in _recall_target_stores()
        ],
        justification={
            "source": JustificationSource.RUNTIME_SIGNAL.value,
            "operation": "recall_mutate_state",
        },
        source=proposal_source,
        metadata={
            "write_intent_kind": WriteIntentKind.RECALL_SIDE_EFFECT.value,
            "mutability": MutabilityLevel.IMPLICIT.value,
        },
    )
    intent = WriteIntent(
        kind=WriteIntentKind.RECALL_SIDE_EFFECT,
        mutability=MutabilityLevel.IMPLICIT,
        proposal=proposal,
        provenance=provenance or build_current_provenance(),
    )
    return bus.emit(intent)


def maybe_emit_recall_side_effect(
    runtime: "BrainMemoryRuntime",
    *,
    query: str,
    top_k: int,
    use_attention: bool,
    activated: List[Dict[str, Any]],
    recall_results: List[Dict[str, Any]],
) -> Optional[str]:
    if not shadow_emit_enabled(config=getattr(runtime, "config", None)):
        return None
    get_bus = getattr(runtime, "_get_write_intent_bus", None)
    if not callable(get_bus):
        return None
    bus = get_bus()
    top_labels = [
        r.get("_label") or r.get("label") or r.get("_layer")
        for r in (activated if use_attention else recall_results[:top_k])
    ]
    return emit_recall_side_effect_intent(
        bus,
        query=query,
        top_k=top_k,
        use_attention=use_attention,
        activated_count=len(activated if use_attention else recall_results[:top_k]),
        top_labels=top_labels,
    )
