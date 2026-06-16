"""Causal overlay for token-influenced hot paths."""

from __future__ import annotations

from typing import Any


def build_influence_overlay(reweighted_graph: dict[str, Any], *, threshold: float = 2.0) -> dict[str, Any]:
    hot_paths: list[dict[str, Any]] = []
    edges = reweighted_graph.get("edges") or []
    max_weight = 1.0

    for edge in edges:
        weight = float(edge.get("token_weight") or 1.0)
        max_weight = max(max_weight, weight)
        if weight > threshold:
            hot_paths.append({
                "from": edge.get("from"),
                "to": edge.get("to"),
                "severity": "HIGH" if weight > threshold * 1.2 else "MEDIUM",
                "weight": weight,
            })

    return {
        "hot_paths": hot_paths,
        "max_weight": round(max_weight, 3),
    }
