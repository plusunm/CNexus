"""L3-G3 — power field optimization report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.l3.field_optimization.types import (
    OptimizationResult,
    PowerField,
    StabilityLandscape,
)
from core.governance.semantic_safety.envelope import with_observational_safety


@dataclass
class L3G3Report:
    stability: dict[str, Any]
    attractor_map: dict[str, Any]
    optimization: dict[str, Any]
    system_phase: str
    power_field: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return with_observational_safety(
            {
                "report": "L3-G3 Power Field Optimization Report",
                "stability": self.stability,
                "attractor_map": self.attractor_map,
                "optimization": self.optimization,
                "system_phase": self.system_phase,
                "system_phase_classification": self.system_phase,
                "power_field": self.power_field,
                "metadata": self.metadata,
                "semantic_note": "system_phase is a descriptive classification — not a runtime mode",
            }
        )

    def render_text(self) -> str:
        lines = [
            "=== L3-G3 Power Field Optimization Report ===",
            f"System phase: {self.system_phase}",
            f"Stability: {self.stability}",
            f"Attractors: {self.attractor_map}",
            "",
            "--- Simulated Optimization (non-executing) ---",
        ]
        for item in self.optimization.get("simulated_optimization", []):
            label = item.get("simulated_adjustment_label", item.get("action", ""))
            lines.append(f"- {item.get('node')}: {label} (Δentropy≈{item.get('expected_entropy_delta')})")
        lines.extend(
            [
                "",
                f"Note: {self.optimization.get('note', '')}",
                "",
                "(L3-G3: stability field solver — zero execution / zero runtime writeback)",
            ]
        )
        return "\n".join(lines)


class L3G3Reporter:
    def render(
        self,
        stability: StabilityLandscape,
        attractors: dict[str, Any],
        optimization: OptimizationResult,
        *,
        power_field: PowerField | None = None,
    ) -> L3G3Report:
        if stability.entropy < 0.3:
            phase = "stable field"
        elif stability.lock_in_regions > 0.6:
            phase = "over-constrained field"
        elif stability.bifurcation_points >= 2:
            phase = "metastable field"
        else:
            phase = "diffuse field"

        return L3G3Report(
            stability={
                "entropy": stability.entropy,
                "lock_in": stability.lock_in_regions,
                "diffusion": stability.diffusion_regions,
                "bifurcation": stability.bifurcation_points,
            },
            attractor_map=attractors,
            optimization=optimization.to_dict(),
            system_phase=phase,
            power_field=power_field.to_dict() if power_field else {},
            metadata={
                "l3_layer": "governance_boundary_g3",
                "read_only": True,
                "optimization_shadow_only": True,
                "no_execution": True,
                "no_action_recommendation": True,
                "no_runtime_writeback": True,
            },
        )
