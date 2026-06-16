"""Kernel execution graph — planned DAG (not post-hoc spine projection)."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

from core.kernel.intent import ExecutionIntent

NodeStatus = Literal["pending", "running", "done", "failed", "skipped"]
EdgeKind = Literal["depends", "fork", "join", "causal"]


def new_node_id(prefix: str = "n") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


@dataclass
class KernelGraphNode:
    node_id: str
    intent: ExecutionIntent
    label: str = ""
    status: NodeStatus = "pending"
    result: Any = None
    error: Optional[str] = None
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["intent"] = self.intent.to_dict()
        if data.get("result") is not None and not isinstance(data["result"], (dict, list, str, int, float, bool, type(None))):
            data["result"] = type(self.result).__name__
        return data


@dataclass
class KernelGraphEdge:
    from_id: str
    to_id: str
    kind: EdgeKind = "depends"
    relation: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if not data.get("relation"):
            data.pop("relation", None)
        return data


@dataclass
class KernelExecutionGraph:
    trace_id: str
    nodes: list[KernelGraphNode] = field(default_factory=list)
    edges: list[KernelGraphEdge] = field(default_factory=list)
    root_node_ids: list[str] = field(default_factory=list)
    join_node_id: Optional[str] = None
    version: str = "execution-graph-kernel-v1"

    @property
    def graph_id(self) -> str:
        return f"{self.trace_id}:{self.invariant_hash()[:12]}"

    def topological_generations(self) -> list[list["KernelGraphNode"]]:
        from core.kernel.graph.resolver import topological_generations

        id_waves = topological_generations(self)
        node_map = self.node_map()
        return [[node_map[nid] for nid in wave] for wave in id_waves]

    def node_map(self) -> dict[str, KernelGraphNode]:
        return {n.node_id: n for n in self.nodes}

    def invariant_hash(self) -> str:
        """Stable graph structure hash — identity becomes graph invariant."""
        label_map = {n.node_id: n.label or n.intent.type for n in self.nodes}
        payload = {
            "version": self.version,
            "nodes": sorted(
                [
                    {
                        "type": n.intent.type,
                        "label": n.label,
                        "deps": sorted(label_map.get(d, d) for d in n.depends_on),
                    }
                    for n in self.nodes
                ],
                key=lambda row: (row["label"], row["type"]),
            ),
            "edges": sorted(
                [
                    {
                        "from": label_map.get(e.from_id, e.from_id),
                        "to": label_map.get(e.to_id, e.to_id),
                        "kind": e.kind,
                    }
                    for e in self.edges
                ],
                key=lambda row: (row["from"], row["to"], row["kind"]),
            ),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return f"G-{digest[:16]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "trace_id": self.trace_id,
            "graph_invariant": self.invariant_hash(),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "roots": self.root_node_ids,
            "join": self.join_node_id,
        }

    def sink_node_id(self) -> str:
        if self.join_node_id:
            return self.join_node_id
        outgoing = {e.from_id for e in self.edges}
        sinks = [n.node_id for n in self.nodes if n.node_id not in outgoing]
        return sinks[-1] if sinks else (self.nodes[-1].node_id if self.nodes else "")
