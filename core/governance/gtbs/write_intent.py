"""CP-1.5 — unified write intent types (extends GTBS v1.0 schema via metadata)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from core.governance.gtbs.types import GovernanceProposal, GTBS_VERSION


GTBS_WRITE_INTENT_VERSION = "1.5.0"
GTBS_WRITE_INTENT_MODE = "SHADOW_EMIT"
GTBS_SOFT_COMMIT_MODE = "SOFT_COMMIT"


class WriteIntentKind(str, Enum):
    CAPTURE = "capture"
    RECALL_SIDE_EFFECT = "recall_side_effect"
    CDG_APPLY = "cdg_apply"
    IR_COMMIT = "ir_commit"
    CHAT_DEFERRED = "chat_deferred"
    WORKING_SELF = "working_self"
    GOVERNANCE_CYCLE = "governance_cycle"


class MutabilityLevel(str, Enum):
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    ADVISORY = "advisory"


@dataclass(frozen=True)
class WriteProvenance:
    trace_id: Optional[str] = None
    dispatch_kind: Optional[str] = None
    caller: str = "internal"
    channel: str = "brain-memory-runtime"
    runtime_token: Optional[str] = None
    entry_registry: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "dispatch_kind": self.dispatch_kind,
            "caller": self.caller,
            "channel": self.channel,
            "runtime_token": self.runtime_token,
            "entry_registry": self.entry_registry,
        }


@dataclass
class WriteIntent:
    """Structured write proposal — wraps frozen GovernanceProposal."""

    kind: WriteIntentKind
    mutability: MutabilityLevel
    proposal: GovernanceProposal
    provenance: WriteProvenance = field(default_factory=WriteProvenance)

    @property
    def intent_id(self) -> str:
        return self.proposal.proposal_id

    def to_audit_payload(self) -> Dict[str, Any]:
        base = self.proposal.to_audit_event()
        base.update(
            {
                "write_intent_kind": self.kind.value,
                "mutability": self.mutability.value,
                "gtbs_write_intent_version": GTBS_WRITE_INTENT_VERSION,
                "gtbs_write_intent_mode": GTBS_WRITE_INTENT_MODE,
                "provenance": self.provenance.to_dict(),
            }
        )
        return base
