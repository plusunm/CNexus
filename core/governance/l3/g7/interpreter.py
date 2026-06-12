"""L3-G7 — field-native interpretation (no layer narrative)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.g7.types import AttractorNode, G7_META_CONSTRAINTS, LayerlessKernelState


class LayerlessInterpreter:
    """Generate field-native interpretation — hierarchy is never referenced."""

    def interpret(self, state: LayerlessKernelState) -> dict[str, Any]:
        field = state.field

        if field.entropy > 0.7:
            regime = "high_entropy_field"
        elif field.coherence > 0.7:
            regime = "stable_coherence_field"
        else:
            regime = "transitional_field"

        return {
            "regime": regime,
            "field_state": field.to_dict(),
            "attractor_landscape": self._summarize_attractors(state.attractors),
            "trace_density": len(state.traces),
            "meta": {
                "no_layers": True,
                "interpretation_model": "field-native",
                **G7_META_CONSTRAINTS,
            },
        }

    def _summarize_attractors(self, attractors: list[AttractorNode]) -> dict[str, Any]:
        if not attractors:
            return {"count": 0, "dominant_strength": 0.0, "basin_types": []}
        return {
            "count": len(attractors),
            "dominant_strength": round(max(a.strength for a in attractors), 4),
            "basin_types": sorted({a.basin for a in attractors}),
        }
