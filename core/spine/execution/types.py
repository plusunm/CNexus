"""Execution Spine Layer v1 — semantic execution DAG types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


EXECUTION_PHASES = (
    "trigger",
    "control",
    "execution",
    "mutation",
    "state",
    "feedback",
)

EXECUTION_EDGE_KINDS = (
    "triggers",
    "controls",
    "executes",
    "mutates",
    "observes",
)


@dataclass
class ExecutionNode:
    event_id: str
    trace_id: str
    phase: str
    event_type: str = ""
    entry: Optional[str] = None
    actor: Optional[str] = None
    timestamp: Optional[str] = None
    summary: Optional[str] = None
    payload: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if data.get("payload") is None:
            data.pop("payload", None)
        return data


@dataclass
class ExecutionEdge:
    from_id: str
    to_id: str
    kind: str
    relation: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data.get("relation"):
            data.pop("relation", None)
        return data


@dataclass
class ExecutionGraph:
    trace_id: str
    nodes: list[ExecutionNode] = field(default_factory=list)
    edges: list[ExecutionEdge] = field(default_factory=list)
    root_events: list[str] = field(default_factory=list)
    version: str = "execution-spine-v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "trace_id": self.trace_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "roots": self.root_events,
        }
