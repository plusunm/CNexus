"""L8 — semantic tensor core (observability + governance + safety → unified tensor)."""

from __future__ import annotations

from typing import Any

_DIMENSIONS = ("observation", "simulation", "collapse", "safety", "governance")


class SemanticTensorCore:
    def tensorize(
        self,
        observability: dict[str, Any],
        governance: dict[str, Any],
        safety: dict[str, Any],
    ) -> dict[str, Any]:
        gov_flat = governance if all(isinstance(v, (int, float)) for v in governance.values()) else {}
        obs_score = float(observability.get("stream_density", 0.5))
        sim_score = float(gov_flat.get("simulation_shadow", 0.4))
        collapse_score = float(gov_flat.get("collapse_stability", 0.4))
        safety_score = float(safety.get("constraint_strength", 0.5))
        gov_score = round(sum(gov_flat.values()) / max(len(gov_flat), 1), 4) if gov_flat else 0.45

        vector = [
            round(obs_score, 4),
            round(sim_score, 4),
            round(collapse_score, 4),
            round(safety_score, 4),
            round(gov_score, 4),
        ]
        return {
            "dimensions": list(_DIMENSIONS),
            "vector": vector,
            "representation": "semantic_tensor",
        }

    def project(self, tensor: dict[str, Any], *, dimensions: str = "collapsed") -> dict[str, Any]:
        vector = tensor.get("vector") or [0.5] * 5
        collapsed = round(sum(vector) / len(vector), 4) if vector else 0.5
        return {
            **tensor,
            "projection": dimensions,
            "collapsed_scalar": collapsed,
            "field_reasoning": True,
        }

    def stability_score(self, tensor: dict[str, Any]) -> float:
        vector = tensor.get("vector") or [0.5]
        collapsed = tensor.get("collapsed_scalar")
        if collapsed is None:
            collapsed = sum(vector) / len(vector)
        # Higher collapse + lower safety → lower stability (observational metric)
        collapse = vector[2] if len(vector) > 2 else 0.4
        safety = vector[3] if len(vector) > 3 else 0.5
        return round(max(0.0, min(1.0, collapsed * 0.5 + safety * 0.35 - collapse * 0.15)), 4)

    def compute_coherence(self, tensor: dict[str, Any]) -> float:
        vector = tensor.get("vector") or [0.5]
        if len(vector) < 2:
            return 0.5
        mean = sum(vector) / len(vector)
        variance = sum((x - mean) ** 2 for x in vector) / len(vector)
        return round(max(0.0, min(1.0, 1.0 - variance)), 4)
