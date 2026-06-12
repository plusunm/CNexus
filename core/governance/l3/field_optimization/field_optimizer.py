"""L3-G3 — gradient-free field optimization simulator (simulation only, no execution)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.field_optimization.types import OptimizationResult, PowerField, StabilityLandscape


class FieldOptimizationSimulator:
    """Simulate which structural changes would reduce field entropy — never actuate."""

    def simulate(self, field: PowerField, landscape: StabilityLandscape) -> OptimizationResult:
        suggestions: list[dict[str, Any]] = []
        total_delta = 0.0

        for node_id, node in field.nodes.items():
            if node_id == "system_core":
                continue

            if node.strength > 0.8:
                delta = -0.1
                suggestions.append(
                    {
                        "node": node_id,
                        "simulated_adjustment_label": "reduce_constraint_weight (simulated)",
                        "expected_entropy_delta": delta,
                    }
                )
                total_delta += delta

            if node.elasticity < 0.2:
                delta = -0.05
                suggestions.append(
                    {
                        "node": node_id,
                        "simulated_adjustment_label": "increase elasticity (simulated)",
                        "expected_entropy_delta": delta,
                    }
                )
                total_delta += delta

        return OptimizationResult(
            simulated_optimization=suggestions,
            note="Shadow-only field optimization simulation — zero execution / zero writeback",
            expected_entropy_delta_total=total_delta,
        )

    def optimize(self, field: PowerField, landscape: StabilityLandscape) -> OptimizationResult:
        """Deprecated v1 alias for simulate()."""
        return self.simulate(field, landscape)


FieldOptimizer = FieldOptimizationSimulator  # deprecated v1 alias
