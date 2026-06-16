"""Token Causal Influence Engine v1 — cost-distorted causal edge weights."""

from __future__ import annotations

import math
from typing import Any


class TokenCausalInfluenceEngine:
    """Compute node influence and edge weights from token cost field."""

    def compute_node_influence(self, node_tokens: dict[str, float]) -> dict[str, float]:
        influence: dict[str, float] = {}
        for node_id, cost in node_tokens.items():
            influence[node_id] = math.log(1 + cost)
        return influence

    def compute_edge_weight(
        self,
        from_id: str,
        to_id: str,
        node_influence: dict[str, float],
        *,
        base_weight: float = 1.0,
    ) -> float:
        delta = node_influence.get(to_id, 0.0) - node_influence.get(from_id, 0.0)
        return round(base_weight + delta, 3)
