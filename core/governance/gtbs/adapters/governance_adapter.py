"""Governance cycle → WriteIntent (advisory write, shadow emit)."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from core.governance.gtbs.types import GovernanceProposal, JustificationSource, OperationType, StateDelta
from core.governance.gtbs.write_intent import (
    MutabilityLevel,
    WriteIntent,
    WriteIntentKind,
)
from core.governance.gtbs.write_intent_bus import WriteIntentBus, shadow_emit_enabled

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def emit_governance_cycle_intent(
    bus: WriteIntentBus,
    *,
    phase: str = "background",
    pre_keys: Optional[list[str]] = None,
) -> WriteIntent:
    proposal = GovernanceProposal(
        operation_type=OperationType.PARAM_ADJUST,
        deltas=[
            StateDelta(
                target_store="cognitive",  # type: ignore[arg-type]
                payload={"phase": phase, "pre_keys": pre_keys or []},
                description="governance cycle side effects",
            )
        ],
        justification={
            "source": JustificationSource.EPISTEMIC_RISK.value,
            "operation": "governance_cycle",
        },
        source="governance_cycle",
        metadata={
            "write_intent_kind": WriteIntentKind.GOVERNANCE_CYCLE.value,
            "mutability": MutabilityLevel.ADVISORY.value,
        },
    )
    intent = WriteIntent(
        kind=WriteIntentKind.GOVERNANCE_CYCLE,
        mutability=MutabilityLevel.ADVISORY,
        proposal=proposal,
    )
    bus.emit(intent)
    return intent


def maybe_emit_governance_cycle_shadow(
    runtime: "BrainMemoryRuntime",
    *,
    phase: str = "background",
    pre_state: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    if not shadow_emit_enabled(config=getattr(runtime, "config", None)):
        return None
    get_bus = getattr(runtime, "_get_write_intent_bus", None)
    if not callable(get_bus):
        return None
    intent = emit_governance_cycle_intent(
        get_bus(),
        phase=phase,
        pre_keys=sorted((pre_state or {}).keys()),
    )
    return intent.intent_id
