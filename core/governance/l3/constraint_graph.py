"""L3-G1 — constraint graph builder from L3-G0 signals."""

from __future__ import annotations

from typing import Any

from core.governance.l3.constraint_model import (
    ConstraintEdge,
    ConstraintGraph,
    ConstraintNode,
    ConstraintType,
)


class ConstraintGraphBuilder:
    """Build constraint topology from L3 probe signals (S15: non-executability)."""

    def build_from_l3_signals(self, l3_signals: dict[str, Any]) -> ConstraintGraph:
        nodes: dict[str, ConstraintNode] = {}
        edges: list[ConstraintEdge] = []

        semantic_weight = 0.6
        if l3_signals.get("type") == "interpretation":
            semantic_weight = min(1.0, 0.6 + float(l3_signals.get("intensity", 0)) * 0.3)
        elif l3_signals.get("type") == "governance_attempt":
            semantic_weight = min(1.0, 0.6 + float(l3_signals.get("intensity", 0)) * 0.4)

        g0 = l3_signals.get("g0_summary") or {}
        if g0.get("governance_attempt", 0) > 0:
            semantic_weight = min(1.0, semantic_weight + 0.15)

        nodes["semantic_layer"] = ConstraintNode(
            id="semantic_layer",
            type=ConstraintType.SEMANTIC,
            weight=semantic_weight,
        )
        nodes["authority_boundary"] = ConstraintNode(
            id="authority_boundary",
            type=ConstraintType.AUTHORITY,
            weight=1.0,
        )
        nodes["runtime_safety"] = ConstraintNode(
            id="runtime_safety",
            type=ConstraintType.SAFETY,
            weight=1.0,
        )
        nodes["attractor_observability"] = ConstraintNode(
            id="attractor_observability",
            type=ConstraintType.STRUCTURAL,
            weight=0.85,
        )

        edges.append(
            ConstraintEdge(
                from_node="semantic_layer",
                to_node="authority_boundary",
                relation="conflicts",
                strength=0.7,
            )
        )
        edges.append(
            ConstraintEdge(
                from_node="authority_boundary",
                to_node="runtime_safety",
                relation="overrides",
                strength=1.0,
            )
        )
        edges.append(
            ConstraintEdge(
                from_node="attractor_observability",
                to_node="semantic_layer",
                relation="depends_on",
                strength=0.5,
            )
        )

        if l3_signals.get("target") == "runtime":
            edges.append(
                ConstraintEdge(
                    from_node="semantic_layer",
                    to_node="runtime_safety",
                    relation="conflicts",
                    strength=min(1.0, 0.5 + float(l3_signals.get("intensity", 0))),
                )
            )

        return ConstraintGraph(nodes=nodes, edges=edges)
