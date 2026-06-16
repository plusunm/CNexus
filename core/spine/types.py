"""CP-2 canonical Spine event schema — query truth layer."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

SPINE_VERSION = "2.0.0"


class SpineEventType(str, Enum):
    DISPATCH = "dispatch"
    RECALL = "recall"
    WRITE_INTENT = "write_intent"
    CDG = "cdg"
    CAPTURE = "capture"
    IR = "ir"
    CHAT = "chat"
    CONTROL = "control"
    STATE = "state"
    LLM_CALL = "llm_call"
    MEMORY_MUTATION = "memory_mutation"
    STATE_PATCH = "state_patch"


class SpineSubsystem(str, Enum):
    RUNTIME = "runtime"
    GTBS = "gtbs"
    CDG = "cdg"
    CONTROL_PLANE = "control_plane"


class SpineAction(str, Enum):
    READ = "read"
    MUTATE = "mutate"
    PROPOSE = "propose"
    COMMIT = "commit"
    REJECT = "reject"


SpineDecision = Literal["ALLOW", "WARN", "REJECT"]


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


@dataclass
class SpineEvent:
    """Unified observability event — canonical query layer."""

    event_id: str
    trace_id: str
    timestamp: str  # ISO8601 UTC
    event_type: str
    subsystem: str
    action: str
    summary: str
    parent_event_id: Optional[str] = None
    causal_links: Optional[list[str]] = None
    decision: Optional[str] = None
    caller: Optional[str] = None
    entry: Optional[str] = None
    hard_gate: bool = False
    state_delta: Optional[dict[str, Any]] = None
    write_intent: Optional[dict[str, Any]] = None
    payload: Optional[dict[str, Any]] = None
    causal_edges: Optional[list[dict[str, Any]]] = None
    spine_version: str = SPINE_VERSION
    gtbs_ref: Optional[dict[str, str]] = None

    @property
    def timestamp_ms(self) -> float:
        return _parse_ts(self.timestamp).timestamp() * 1000

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data.get("causal_links"):
            data.pop("causal_links", None)
        if not data.get("parent_event_id"):
            data.pop("parent_event_id", None)
        if data.get("state_delta") is None:
            data.pop("state_delta", None)
        if data.get("write_intent") is None:
            data.pop("write_intent", None)
        if data.get("payload") is None:
            data.pop("payload", None)
        if not data.get("causal_edges"):
            data.pop("causal_edges", None)
        if data.get("gtbs_ref") is None:
            data.pop("gtbs_ref", None)
        return data

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "SpineEvent":
        return cls(
            event_id=str(row["event_id"]),
            trace_id=str(row["trace_id"]),
            timestamp=str(row["timestamp"]),
            event_type=str(row["event_type"]),
            subsystem=str(row["subsystem"]),
            action=str(row["action"]),
            summary=str(row.get("summary") or ""),
            parent_event_id=row.get("parent_event_id"),
            causal_links=list(row["causal_links"]) if row.get("causal_links") else None,
            decision=row.get("decision"),
            caller=row.get("caller"),
            entry=row.get("entry"),
            hard_gate=bool(row.get("hard_gate", False)),
            state_delta=row.get("state_delta"),
            write_intent=row.get("write_intent"),
            payload=row.get("payload"),
            causal_edges=list(row["causal_edges"]) if row.get("causal_edges") else None,
            spine_version=str(row.get("spine_version") or SPINE_VERSION),
            gtbs_ref=row.get("gtbs_ref"),
        )
