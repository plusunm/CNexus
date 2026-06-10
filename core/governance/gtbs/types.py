"""
GTBS v1.0 — Governance Transaction Boundary Spec (Schema Freeze / P0).

This module defines types only. No runtime logic, no gatekeeper, no write interception.
All future GTBS implementations must conform to this schema.

Status: SCHEMA_FROZE — v1.0 (2026-06-10)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Literal, Optional

GTBS_VERSION = "1.0.0"
GTBS_STATUS = "SCHEMA_FROZEN"


class TransactionState(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"
    COMMITTED = "committed"


class OperationType(str, Enum):
    INGEST = "INGEST"
    PRUNE = "PRUNE"
    STRUCTURAL_MERGE = "STRUCTURAL_MERGE"
    PARAM_ADJUST = "PARAM_ADJUST"
    MEMORY_REWRITE = "MEMORY_REWRITE"
    HOLD = "HOLD"


class JustificationSource(str, Enum):
    L7_CERTIFICATE = "L7_certificate"
    TOPOLOGY_RECONSTRUCTION = "topology_reconstruction"
    EPISTEMIC_RISK = "epistemic_risk"
    RUNTIME_SIGNAL = "runtime_signal"
    INTERACTION = "interaction"


TargetStore = Literal["reality", "cognitive", "storage", "personality", "narrative"]

AuditEventType = Literal["proposal", "approval", "commit", "rejection", "defer"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class StateDelta:
    """Single-store mutation description (declarative, not executed)."""

    target_store: TargetStore
    payload: dict[str, Any]
    description: str = ""


@dataclass
class GovernanceProposal:
    """GTBS v1.0 proposal (P0 frozen)."""

    operation_type: OperationType
    deltas: List[StateDelta]
    justification: dict[str, Any]
    source: str = "interaction"
    proposal_id: str = field(default_factory=lambda: f"prop-{uuid.uuid4().hex[:12]}")
    ts: datetime = field(default_factory=_utcnow)
    constraints: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    expiry_ts: Optional[datetime] = None

    def to_audit_event(self) -> dict[str, Any]:
        return {
            "event_type": "proposal",
            "gtbs_version": GTBS_VERSION,
            "proposal_id": self.proposal_id,
            "ts": self.ts.isoformat(),
            "source": self.source,
            "operation_type": self.operation_type.value,
            "target_stores": [d.target_store for d in self.deltas],
            "justification": self.justification,
        }


@dataclass
class GovernanceTransaction:
    """GTBS v1.0 transaction state-machine carrier (P0 frozen)."""

    proposal: GovernanceProposal
    state: TransactionState = TransactionState.PROPOSED
    cdg_decision: Optional[dict[str, Any]] = None
    approval: Optional[dict[str, Any]] = None
    commit_receipt: Optional[dict[str, Any]] = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    @property
    def transaction_id(self) -> str:
        return self.proposal.proposal_id

    def transition_to(
        self,
        new_state: TransactionState,
        payload: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record state transition (minimal FSM; enforcement deferred to v1.1+)."""
        self.state = new_state
        self.updated_at = _utcnow()
        if not payload:
            return
        if new_state == TransactionState.APPROVED:
            self.approval = payload
        elif new_state == TransactionState.COMMITTED:
            self.commit_receipt = payload
        elif new_state == TransactionState.REJECTED:
            self.approval = payload


@dataclass
class AuditTransactionEvent:
    """GTBS audit event — parallel to existing governance cycle JSONL, not a replacement."""

    event_type: AuditEventType
    transaction_id: str
    payload: dict[str, Any]
    ts: datetime = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "gtbs_version": GTBS_VERSION,
            "transaction_id": self.transaction_id,
            "ts": self.ts.isoformat(),
            "payload": self.payload,
        }
