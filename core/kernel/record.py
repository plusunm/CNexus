"""ExecutionRecord — single source of execution truth (CP-3 consolidation)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from core.kernel.context import ExecutionContext
from core.kernel.intent import ExecutionIntent

RECORD_VERSION = "execution-record-v1"


@dataclass
class ExecutionRecord:
    """
    Canonical execution truth unit.

    All projections (identity, spine, tap, replay, explain) derive from this record.
    """

    trace_id: str
    intent_type: str
    result: Any
    identity: Optional[str] = None
    graph_invariant: Optional[str] = None
    graph: Optional[dict[str, Any]] = None
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    equivalence: Optional[dict[str, Any]] = None
    replay_signature: Optional[str] = None
    state_projection: dict[str, Any] = field(default_factory=dict)
    causal_projection: dict[str, Any] = field(default_factory=dict)
    explain_projection: dict[str, Any] = field(default_factory=dict)
    audit: dict[str, Any] = field(default_factory=dict)
    audit_log: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    derivation: dict[str, Any] = field(default_factory=dict)
    version: str = RECORD_VERSION
    elapsed_ms: float = 0.0

    @classmethod
    def materialize_lazy(
        cls,
        *,
        intent: ExecutionIntent,
        ctx: ExecutionContext,
        result: Any,
        tier: str,
        identity_info: Optional[dict[str, Any]] = None,
    ) -> "LazyExecutionRecord":
        """Minimal record for T0/T1 — projections expanded on demand."""
        identity = (identity_info or {}).get("identity")
        equivalence = (identity_info or {}).get("equivalence")
        record = LazyExecutionRecord(
            trace_id=ctx.trace_id,
            intent_type=intent.type,
            result=result,
            identity=identity,
            equivalence=equivalence,
            elapsed_ms=ctx.elapsed_ms(),
            audit={
                "source": intent.source,
                "intent": intent.type,
                "execution_tier": tier,
            },
            audit_log={
                "source": intent.source,
                "intent": intent.type,
                "execution_tier": tier,
            },
            derivation={
                "execution_tier": tier,
                "lazy": True,
            },
        )
        record.state_projection = cls._build_state_projection(intent, result)
        record.explain_projection = {"execution_tier": tier, "lazy": True}
        record.causal_projection = {}
        return record

    @classmethod
    def materialize(
        cls,
        *,
        intent: ExecutionIntent,
        ctx: ExecutionContext,
        result: Any,
        graph: Any = None,
        identity_info: Optional[dict[str, Any]] = None,
    ) -> "ExecutionRecord":
        graph_dict = graph.to_dict() if graph is not None else None
        identity = (identity_info or {}).get("identity")
        equivalence = (identity_info or {}).get("equivalence")
        execution_tier = (identity_info or {}).get("execution_tier")

        audit_base = {
            "source": intent.source,
            "intent": intent.type,
            "graph_id": getattr(graph, "graph_id", None) if graph is not None else None,
        }
        if execution_tier:
            audit_base["execution_tier"] = execution_tier

        record = cls(
            trace_id=ctx.trace_id,
            intent_type=intent.type,
            result=result,
            identity=identity,
            graph_invariant=graph.invariant_hash() if graph is not None else None,
            graph=graph_dict,
            nodes=list((graph_dict or {}).get("nodes") or []),
            edges=list((graph_dict or {}).get("edges") or []),
            equivalence=equivalence,
            elapsed_ms=ctx.elapsed_ms(),
            audit=audit_base,
            audit_log=dict(audit_base),
            derivation={
                "scheduler": result.get("scheduler") if isinstance(result, dict) else None,
                "node_count": len((graph_dict or {}).get("nodes") or []),
                "execution_tier": execution_tier,
            },
        )
        record.state_projection = cls._build_state_projection(intent, result)
        record.causal_projection = cls._build_causal_projection(graph_dict, result)
        record.explain_projection = dict(record.derivation)
        record.audit_log = dict(record.audit)
        if graph_dict:
            record.events.append(
                {
                    "type": "execution_graph_materialized",
                    "graph_invariant": record.graph_invariant,
                    "identity": record.identity,
                }
            )
        return record

    @staticmethod
    def _build_state_projection(intent: ExecutionIntent, result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            keys = ("ok", "status", "skipped", "reason", "stability_metrics", "total", "by_layer")
            return {k: result[k] for k in keys if k in result}
        return {"intent": intent.type, "result_type": type(result).__name__}

    @staticmethod
    def _build_causal_projection(
        graph_dict: Optional[dict[str, Any]], result: Any
    ) -> dict[str, Any]:
        edges = list((graph_dict or {}).get("edges") or [])
        nodes = list((graph_dict or {}).get("nodes") or [])
        return {
            "edge_count": len(edges),
            "node_count": len(nodes),
            "edges": edges[:32],
            "scheduler": result.get("scheduler") if isinstance(result, dict) else None,
        }

    def to_dict(self) -> dict[str, Any]:
        data = {
            "version": self.version,
            "trace_id": self.trace_id,
            "intent_type": self.intent_type,
            "result": self.result,
            "identity": self.identity,
            "graph_invariant": self.graph_invariant,
            "graph": self.graph,
            "nodes": self.nodes,
            "edges": self.edges,
            "equivalence": self.equivalence,
            "replay_signature": self.replay_signature,
            "state_projection": self.state_projection,
            "causal_projection": self.causal_projection,
            "explain_projection": self.explain_projection,
            "audit_log": self.audit_log or self.audit,
            "audit": self.audit,
            "events": self.events,
            "derivation": self.derivation,
            "elapsed_ms": self.elapsed_ms,
        }
        from core.kernel.schema.schema_lock import validate_execution_record

        validate_execution_record(data, strict=True)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionRecord":
        return cls(
            trace_id=str(data.get("trace_id") or ""),
            intent_type=str(data.get("intent_type") or ""),
            result=data.get("result"),
            identity=data.get("identity"),
            graph_invariant=data.get("graph_invariant"),
            graph=data.get("graph"),
            nodes=list(data.get("nodes") or []),
            edges=list(data.get("edges") or []),
            equivalence=data.get("equivalence"),
            replay_signature=data.get("replay_signature"),
            state_projection=dict(data.get("state_projection") or {}),
            causal_projection=dict(data.get("causal_projection") or {}),
            explain_projection=dict(data.get("explain_projection") or {}),
            audit=dict(data.get("audit") or {}),
            audit_log=dict(data.get("audit_log") or data.get("audit") or {}),
            events=list(data.get("events") or []),
            derivation=dict(data.get("derivation") or {}),
            version=str(data.get("version") or RECORD_VERSION),
            elapsed_ms=float(data.get("elapsed_ms") or 0.0),
        )

    def to_legacy_response(self) -> Any:
        """Backward-compatible response for dispatcher / runtime proxy."""
        node_count = len(self.nodes)
        if node_count <= 1 and not isinstance(self.result, dict):
            return self.result
        if isinstance(self.result, dict):
            out = dict(self.result)
            out.setdefault("trace_id", self.trace_id)
            if self.identity:
                out.setdefault("identity", self.identity)
                out.setdefault("identity_id", self.identity)
            if self.equivalence:
                out.setdefault("equivalence", self.equivalence)
            return out
        return self.result

    def with_replay_signature(self, signature: str) -> "ExecutionRecord":
        self.replay_signature = signature
        return self

    def build_store_projection(self) -> dict[str, Any]:
        """Runbook Σ.M store projection — external to frozen v1 schema."""
        from core.evolved.store_step import build_store_projection

        return build_store_projection(self)

    def build_sigma_trace(self) -> dict[str, Any]:
        """Runbook Σ.T trace projection — external to frozen v1 schema."""
        from core.evolved.sigma_mapping import execution_record_to_sigma_trace

        return execution_record_to_sigma_trace(self)


@dataclass
class LazyExecutionRecord(ExecutionRecord):
    """Deferred projection build for fast execution tiers."""

    _lazy: bool = True
    _expanded: bool = False

    def expand(self) -> "LazyExecutionRecord":
        if self._expanded:
            return self
        tier = str((self.derivation or {}).get("execution_tier") or "T0")
        self.causal_projection = {
            "edge_count": 0,
            "node_count": 0,
            "edges": [],
            "execution_tier": tier,
        }
        self.explain_projection = dict(self.derivation or {})
        self.events.append(
            {
                "type": "lazy_record_expanded",
                "execution_tier": tier,
            }
        )
        self._expanded = True
        return self

    def to_dict(self) -> dict[str, Any]:
        if self._lazy and not self._expanded:
            self.expand()
        return super().to_dict()
