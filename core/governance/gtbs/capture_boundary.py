"""GTBS v1.2 — capture() single-path propose-commit pilot.

Runtime remains commit authority. CDG is not in the hot path;
existing CaptureFilter + WriteGate perform proposal validation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from core.governance.gtbs.adapters.capture_adapter import (
    build_capture_write_intent,
    infer_capture_target_stores,
)
from core.governance.gtbs.transaction_log import GTBSTransactionLog
from core.governance.gtbs.types import (
    AuditTransactionEvent,
    GovernanceProposal,
    GovernanceTransaction,
    TransactionState,
)
from core.governance.gtbs.write_intent_bus import WriteIntentBus
from core.governance.gtbs.write_funnel import execute_with_tier_a_rollback

GTBS_CAPTURE_VERSION = "1.2.0"
GTBS_CAPTURE_MODE = "CAPTURE_PILOT"


class CaptureMutationBoundary:
    """Propose → validate → approve → commit for capture() only."""

    GTBS_VERSION = GTBS_CAPTURE_VERSION
    GTBS_MODE = GTBS_CAPTURE_MODE

    def __init__(
        self,
        transaction_log: GTBSTransactionLog,
        *,
        write_intent_bus: Optional[WriteIntentBus] = None,
    ) -> None:
        self._log = transaction_log
        self._write_intent_bus = write_intent_bus

    def propose_and_commit(
        self,
        *,
        role: str,
        content: str,
        layer: str,
        importance: float,
        emotional_weight: float,
        meta: Dict[str, Any],
        validate: Callable[[], Tuple[bool, str, float]],
        commit: Callable[[], str],
        runtime: Any = None,
    ) -> Union[str, Dict[str, Any]]:
        intent = build_capture_write_intent(
            role=role,
            content=content,
            layer=layer,
            importance=importance,
            emotional_weight=emotional_weight,
            meta=meta,
            source="capture",
        )
        proposal = intent.proposal
        target_stores = infer_capture_target_stores(
            role=role, layer=layer, importance=importance
        )
        txn = GovernanceTransaction(proposal=proposal)

        if self._write_intent_bus is not None:
            self._write_intent_bus.emit(intent)
        else:
            self._log.append(
                AuditTransactionEvent(
                    event_type="proposal",
                    transaction_id=txn.transaction_id,
                    payload=proposal.to_audit_event(),
                )
            )

        allowed, gate_reason, risk = validate()
        if not allowed:
            txn.transition_to(
                TransactionState.REJECTED,
                payload={"reason": gate_reason, "risk": risk},
            )
            self._log.append(
                _audit_event(txn, "rejection", {"reason": gate_reason, "risk": risk})
            )
            return f"denied: {gate_reason} (risk={risk:.2f})"

        txn.transition_to(
            TransactionState.APPROVED,
            payload={"authority": "runtime", "risk": risk, "gate": "write_gate"},
        )
        self._log.append(
            _audit_event(txn, "approval", {"authority": "runtime", "risk": risk})
        )

        tier_b_meta = {"role": role, "layer": layer, "importance": importance}

        if runtime is not None:
            memory_id = execute_with_tier_a_rollback(
                runtime,
                commit,
                intent_id=intent.intent_id,
                tier_b_meta=tier_b_meta,
                record_commit=False,
            )
        else:
            memory_id = commit()
        txn.transition_to(
            TransactionState.COMMITTED,
            payload={
                "memory_id": memory_id,
                "committed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        self._log.append(
            _audit_event(
                txn,
                "commit",
                {
                    "memory_id": memory_id,
                    "target_stores": target_stores,
                    "tier_b_meta": tier_b_meta,
                },
            )
        )
        return memory_id


def _audit_event(
    txn: GovernanceTransaction,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
) -> AuditTransactionEvent:
    return AuditTransactionEvent(
        event_type=event_type,  # type: ignore[arg-type]
        transaction_id=txn.transaction_id,
        payload=dict(payload or {}),
    )
