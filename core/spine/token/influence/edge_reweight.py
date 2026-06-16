"""Reweight causal edges with token influence."""

from __future__ import annotations

from typing import Any

from core.spine.token.influence.influence_engine import TokenCausalInfluenceEngine


def reweight_causal_edges(subgraph: dict[str, Any], token_field: dict[str, float]) -> dict[str, Any]:
    engine = TokenCausalInfluenceEngine()
    node_influence = engine.compute_node_influence(token_field)

    new_edges: list[dict[str, Any]] = []
    for edge in subgraph.get("edges") or []:
        from_id = str(edge.get("from") or "")
        to_id = str(edge.get("to") or "")
        weight = engine.compute_edge_weight(from_id, to_id, node_influence)
        new_edges.append({
            **edge,
            "base_weight": 1.0,
            "token_weight": weight,
            "influenced": True,
        })

    return {
        "nodes": subgraph.get("nodes") or [],
        "edges": new_edges,
    }
