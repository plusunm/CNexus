"""Observation layer — read-only ExecutionRecord projection (single truth view)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.kernel.kernel import ExecutionKernel
    from core.kernel.record import ExecutionRecord


@dataclass(frozen=True)
class ExecutionRecordView:
    """UI/API observation surface derived only from ExecutionRecord."""

    trace_id: str
    identity: Optional[str]
    graph: Optional[dict[str, Any]]
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    state_projection: dict[str, Any]
    causal_projection: dict[str, Any]
    explain_projection: dict[str, Any]
    replay_signature: Optional[str]
    audit_log: dict[str, Any]
    intent_type: str
    elapsed_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "identity": self.identity,
            "graph": self.graph,
            "nodes": self.nodes,
            "edges": self.edges,
            "state_projection": self.state_projection,
            "causal_projection": self.causal_projection,
            "explain_projection": self.explain_projection,
            "replay_signature": self.replay_signature,
            "audit_log": self.audit_log,
            "intent_type": self.intent_type,
            "elapsed_ms": self.elapsed_ms,
        }


def from_record(record: "ExecutionRecord") -> ExecutionRecordView:
    data = record.to_dict()
    return ExecutionRecordView(
        trace_id=data["trace_id"],
        identity=data.get("identity"),
        graph=data.get("graph"),
        nodes=list(data.get("nodes") or []),
        edges=list(data.get("edges") or []),
        state_projection=dict(data.get("state_projection") or {}),
        causal_projection=dict(data.get("causal_projection") or {}),
        explain_projection=dict(data.get("explain_projection") or {}),
        replay_signature=data.get("replay_signature"),
        audit_log=dict(data.get("audit_log") or data.get("audit") or {}),
        intent_type=data.get("intent_type", ""),
        elapsed_ms=float(data.get("elapsed_ms") or 0.0),
    )


def read(trace_id: str, kernel: "ExecutionKernel") -> ExecutionRecordView:
    """唯一合法观测读取 — load ExecutionRecord by trace."""
    record = kernel.get_record(trace_id)
    if record is not None:
        return from_record(record)
    from core.kernel.observe.tap_fallback import build_record_dict_from_tap, tap_events_for_trace

    events = tap_events_for_trace(trace_id)
    if not events:
        raise KeyError(f"execution record not found: {trace_id}")
    data = build_record_dict_from_tap(trace_id, events)
    return ExecutionRecordView(
        trace_id=data["trace_id"],
        identity=data.get("identity"),
        graph=data.get("graph"),
        nodes=list(data.get("nodes") or []),
        edges=list(data.get("edges") or []),
        state_projection=dict(data.get("state_projection") or {}),
        causal_projection=dict(data.get("causal_projection") or {}),
        explain_projection=dict(data.get("explain_projection") or {}),
        replay_signature=data.get("replay_signature"),
        audit_log=dict(data.get("audit_log") or {}),
        intent_type=str(data.get("intent_type") or ""),
        elapsed_ms=float(data.get("elapsed_ms") or 0.0),
    )
