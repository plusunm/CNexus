"""
GTBS v1.2 — capture() single-path propose-commit pilot.

Runtime remains commit authority. CDG is not in the hot path;
existing CaptureFilter + WriteGate perform proposal validation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from core.governance.gtbs.transaction_log import GTBSTransactionLog
from core.governance.gtbs.types import (
    AuditTransactionEvent,
    GovernanceProposal,
    GovernanceTransaction,
    JustificationSource,
    OperationType,
    StateDelta,
    TransactionState,
)

GTBS_CAPTURE_VERSION = "1.2.0"
GTBS_CAPTURE_MODE = "CAPTURE_PILOT"


def infer_capture_target_stores(
    *,
    role: str,
    layer: str,
    importance: float,
) -> List[str]:
    stores = ["storage"]
    if layer in ("goal", "identity", "belief"):
        stores.append("narrative")
    if importance > 0.75:
        stores.append("belief")
    if role == "user":
        stores.append("cognitive")
    return sorted(set(stores))


class CaptureMutationBoundary:
    """Propose → validate → approve → commit for capture() only."""

    GTBS_VERSION = GTBS_CAPTURE_VERSION
    GTBS_MODE = GTBS_CAPTURE_MODE

    def __init__(self, transaction_log: GTBSTransactionLog) -> None:
        self._log = transaction_log

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
    ) -> Union[str, Dict[str, Any]]:
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
            source="capture",
            metadata={"gtbs_mode": self.GTBS_MODE, "gtbs_version": self.GTBS_VERSION},
        )
        txn = GovernanceTransaction(proposal=proposal)
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

        memory_id = commit()
        txn.transition_to(
            TransactionState.COMMITTED,
            payload={
                "memory_id": memory_id,
                "committed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        self._log.append(
            _audit_event(txn, "commit", {"memory_id": memory_id, "target_stores": target_stores})
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
