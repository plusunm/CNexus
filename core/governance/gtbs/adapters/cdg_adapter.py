"""CDG apply_cdg_state → WriteIntent (advisory write, shadow emit)."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from core.governance.gtbs.adapters.capture_adapter import summarize_cdg_modified_state
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


def _cdg_target_stores(modified_state: Dict[str, Any]) -> list[str]:
    stores: list[str] = []
    if modified_state.get("working_self"):
        stores.append("cognitive")
    if modified_state.get("self_model") or modified_state.get("beliefs"):
        stores.extend(["personality", "narrative"])
    if modified_state.get("flags"):
        stores.append("narrative")
    return sorted(set(stores)) or ["cognitive"]


def build_cdg_apply_write_intent(
    *,
    phase: str,
    pre_state: Dict[str, Any],
    proposed_state: Dict[str, Any],
    modified_state: Dict[str, Any],
    decision_summary: Optional[Dict[str, Any]] = None,
    provenance: Optional[WriteProvenance] = None,
) -> WriteIntent:
    summary = summarize_cdg_modified_state(modified_state)
    target_stores = _cdg_target_stores(modified_state)
    proposal = GovernanceProposal(
        operation_type=OperationType.PARAM_ADJUST,
        deltas=[
            StateDelta(
                target_store=store,  # type: ignore[arg-type]
                payload={
                    "phase": phase,
                    "cdg_apply": True,
                    **summary,
                },
                description=f"cdg apply → {store}",
            )
            for store in target_stores
        ],
        justification={
            "source": JustificationSource.EPISTEMIC_RISK.value,
            "phase": phase,
            "pre_keys": sorted(pre_state.keys()),
            "proposed_keys": sorted(proposed_state.keys()),
        },
        source="cdg_apply",
        metadata={
            "write_intent_kind": WriteIntentKind.CDG_APPLY.value,
            "mutability": MutabilityLevel.ADVISORY.value,
            "decision_summary": decision_summary or {},
        },
    )
    return WriteIntent(
        kind=WriteIntentKind.CDG_APPLY,
        mutability=MutabilityLevel.ADVISORY,
        proposal=proposal,
        provenance=provenance or build_current_provenance(),
    )


def emit_cdg_apply_write_intent(
    bus: WriteIntentBus,
    *,
    phase: str,
    pre_state: Dict[str, Any],
    proposed_state: Dict[str, Any],
    modified_state: Dict[str, Any],
    decision_summary: Optional[Dict[str, Any]] = None,
) -> WriteIntent:
    intent = build_cdg_apply_write_intent(
        phase=phase,
        pre_state=pre_state,
        proposed_state=proposed_state,
        modified_state=modified_state,
        decision_summary=decision_summary,
    )
    bus.emit(intent)
    return intent


def maybe_emit_cdg_apply_shadow(
    runtime: "BrainMemoryRuntime",
    *,
    phase: str,
    pre_state: Dict[str, Any],
    proposed_state: Dict[str, Any],
    modified_state: Dict[str, Any],
    decision_summary: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    if not shadow_emit_enabled(config=getattr(runtime, "config", None)):
        return None
    get_bus = getattr(runtime, "_get_write_intent_bus", None)
    if not callable(get_bus):
        return None
    intent = emit_cdg_apply_write_intent(
        get_bus(),
        phase=phase,
        pre_state=pre_state,
        proposed_state=proposed_state,
        modified_state=modified_state,
        decision_summary=decision_summary,
    )
    return intent.intent_id
