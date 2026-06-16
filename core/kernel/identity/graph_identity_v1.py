"""Graph Identity Kernel v1 — semantic equivalence over execution graphs."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from core.kernel.graph.execution_graph import KernelExecutionGraph

IDENTITY_VERSION = "graph-identity-v1"
NOISE_PAYLOAD_KEYS = frozenset(
    {
        "trace_id",
        "timestamp",
        "request_id",
        "_kernel_internal",
        "_bypass_kernel",
        "_upstream",
    }
)


class GraphIdentityV1:
    """
    Execution Graph Identity Kernel v1.

    Determines whether two graphs are semantically equivalent:
    - node intent types + canonical dependency labels
    - edge topology (by label, not ephemeral node id)
    - normalized payload (runtime noise stripped)
    """

    def __init__(self, *, normalize_payload: bool = True) -> None:
        self.normalize_payload = normalize_payload

    def compute_identity(self, graph: KernelExecutionGraph) -> str:
        canonical = self._canonicalize(graph)
        digest = self._hash(canonical)
        return f"I-{digest[:16]}"

    def equivalent(self, g1: KernelExecutionGraph, g2: KernelExecutionGraph) -> bool:
        return self._canonicalize(g1) == self._canonicalize(g2)

    def canonical_form(self, graph: KernelExecutionGraph) -> dict[str, Any]:
        return self._canonicalize(graph)

    def _canonicalize(self, graph: KernelExecutionGraph) -> dict[str, Any]:
        label_map = {n.node_id: n.label or n.intent.type for n in graph.nodes}

        nodes = []
        for node in graph.nodes:
            dep_labels = sorted(label_map.get(dep, dep) for dep in node.depends_on)
            nodes.append(
                {
                    "type": node.intent.type,
                    "label": node.label or node.intent.type,
                    "deps": dep_labels,
                    "payload": self._normalize_payload(node.intent.payload),
                }
            )
        nodes.sort(key=lambda row: (row["type"], row["label"], str(row["deps"])))

        edges = sorted(
            (
                label_map.get(edge.from_id, edge.from_id),
                label_map.get(edge.to_id, edge.to_id),
                edge.kind,
            )
            for edge in graph.edges
        )

        return {
            "version": IDENTITY_VERSION,
            "nodes": nodes,
            "edges": edges,
            "graph_type": "kernel_execution_dag",
        }

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        if not self.normalize_payload:
            return dict(payload)

        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            if key in NOISE_PAYLOAD_KEYS:
                continue
            if key.startswith("_") and key not in {"_action"}:
                continue
            if isinstance(value, (dict, list)):
                normalized[key] = json.dumps(value, sort_keys=True, ensure_ascii=False)
            else:
                normalized[key] = value
        return normalized

    def _hash(self, obj: dict[str, Any]) -> str:
        raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
