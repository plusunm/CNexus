"""L3-G3 — power attractor map over constraint field."""

from __future__ import annotations

from typing import Any

from core.governance.l3.field_optimization.types import PowerField


class AttractorMap:
    """Map stable attractor regions in power field (observational only)."""

    def compute(self, field: PowerField) -> dict[str, Any]:
        attractors: list[dict[str, Any]] = []

        for node_id, node in field.nodes.items():
            if node_id == "system_core":
                continue
            score = node.strength * (1.0 - node.elasticity)
            if score > 0.75:
                attractors.append(
                    {
                        "type": "stable_attractor",
                        "node": node_id,
                        "depth": round(score, 4),
                    }
                )
            elif score > 0.45:
                attractors.append(
                    {
                        "type": "metastable_attractor",
                        "node": node_id,
                        "depth": round(score, 4),
                    }
                )

        dominance = max((a["depth"] for a in attractors), default=0.0)
        return {
            "attractors": attractors,
            "dominance": round(dominance, 4),
            "count": len(attractors),
        }
