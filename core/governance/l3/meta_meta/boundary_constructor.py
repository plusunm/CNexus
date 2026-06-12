"""L3-G5 — inter-layer boundary construction and consistency evaluation."""

from __future__ import annotations

from core.governance.l3.meta_meta.types import BoundaryDefinition, LayerDefinition


class BoundaryConstructor:
    """Build and evaluate boundaries between governance layers (observational only)."""

    _BOUNDARY_MAP: dict[tuple[str, str], str] = {
        ("L2", "L3-G0"): "rigid",
        ("L3-G0", "L3-G1"): "reflective",
        ("L3-G1", "L3-G2"): "soft",
        ("L3-G2", "L3-G3"): "reflective",
        ("L3-G3", "L3-G4"): "recursive",
        ("L3-G4", "L3-G5"): "recursive",
    }

    def construct(self, layers: list[LayerDefinition]) -> list[BoundaryDefinition]:
        boundaries: list[BoundaryDefinition] = []
        names = [layer.name for layer in layers]
        for i in range(len(names) - 1):
            upper, lower = names[i], names[i + 1]
            btype = self._BOUNDARY_MAP.get((upper, lower), "reflective")
            boundaries.append(
                BoundaryDefinition(
                    upper_layer=upper,
                    lower_layer=lower,
                    boundary_type=btype,
                )
            )
        return boundaries

    def evaluate_consistency(self, boundaries: list[BoundaryDefinition]) -> float:
        if not boundaries:
            return 1.0
        valid = sum(1 for b in boundaries if b.boundary_type != "undefined")
        recursive_penalty = sum(0.05 for b in boundaries if b.boundary_type == "recursive")
        base = valid / len(boundaries)
        return max(0.0, min(1.0, base - recursive_penalty * 0.5))
