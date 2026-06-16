"""Capture → WriteIntent (explicit write, shadow + GTBS pilot FSM)."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from core.governance.gtbs.types import GovernanceProposal, JustificationSource, OperationType, StateDelta
from core.governance.gtbs.write_intent import (
    MutabilityLevel,
    WriteIntent,
    WriteIntentKind,
    WriteProvenance,
)
from core.governance.gtbs.write_intent_bus import WriteIntentBus, build_current_provenance, shadow_emit_enabled

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def infer_capture_target_stores(
    *,
    role: str,
    layer: str,
    importance: float,
) -> list[str]:
    stores = ["storage"]
    if layer in ("goal", "identity", "belief"):
        stores.append("narrative")
    if importance > 0.75:
        stores.append("belief")
    if role == "user":
        stores.append("cognitive")
    return sorted(set(stores))


def build_capture_write_intent(
    *,
    role: str,
    content: str,
    layer: str,
    importance: float,
    emotional_weight: float = 0.5,
    meta: Optional[Dict[str, Any]] = None,
    source: str = "capture",
    provenance: Optional[WriteProvenance] = None,
) -> WriteIntent:
    target_stores = infer_capture_target_stores(
        role=role, layer=layer, importance=importance
    )
    proposal = GovernanceProposal(
        operation_type=OperationType.INGEST,
        deltas=[
            StateDelta(
                target_store=store,  # type: ignore[arg-type]
                payload={
                    "role": role,
                    "layer": layer,
                    "importance": importance,
                    "emotional_weight": emotional_weight,
                    "content_preview": content[:120],
                },
                description=f"capture ingest → {store}",
            )
            for store in target_stores
        ],
        justification={
            "source": JustificationSource.INTERACTION.value,
            "role": role,
            "layer": layer,
            "importance": importance,
        },
        source=source,
        metadata={
            "write_intent_kind": WriteIntentKind.CAPTURE.value,
            "mutability": MutabilityLevel.EXPLICIT.value,
            "meta_keys": sorted((meta or {}).keys()),
        },
    )
    return WriteIntent(
        kind=WriteIntentKind.CAPTURE,
        mutability=MutabilityLevel.EXPLICIT,
        proposal=proposal,
        provenance=provenance or build_current_provenance(),
    )


def emit_capture_write_intent(
    bus: WriteIntentBus,
    *,
    role: str,
    content: str,
    layer: str,
    importance: float,
    emotional_weight: float = 0.5,
    meta: Optional[Dict[str, Any]] = None,
    source: str = "capture",
) -> WriteIntent:
    intent = build_capture_write_intent(
        role=role,
        content=content,
        layer=layer,
        importance=importance,
        emotional_weight=emotional_weight,
        meta=meta,
        source=source,
    )
    bus.emit(intent)
    return intent


def maybe_emit_capture_direct_shadow(
    runtime: "BrainMemoryRuntime",
    *,
    role: str,
    content: str,
    layer: str,
    importance: float,
    emotional_weight: float = 0.5,
    meta: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Shadow emit for capture() when GTBS capture pilot is off."""
    if not shadow_emit_enabled(config=getattr(runtime, "config", None)):
        return None
    get_bus = getattr(runtime, "_get_write_intent_bus", None)
    if not callable(get_bus):
        return None
    intent = emit_capture_write_intent(
        get_bus(),
        role=role,
        content=content,
        layer=layer,
        importance=importance,
        emotional_weight=emotional_weight,
        meta=meta,
        source="capture_direct",
    )
    return intent.intent_id


def summarize_cdg_modified_state(modified_state: Dict[str, Any]) -> Dict[str, Any]:
    flags = modified_state.get("flags") or []
    return {
        "modified_keys": sorted(modified_state.keys()),
        "belief_count": len(modified_state.get("beliefs") or []),
        "flag_count": len(flags),
        "flags_preview": list(flags)[:8],
        "has_working_self": bool(modified_state.get("working_self")),
        "has_self_model": bool(modified_state.get("self_model")),
    }
