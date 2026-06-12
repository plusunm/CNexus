"""L3-G5 — meta-layer engine orchestrating level-of-levels metrics."""

from __future__ import annotations

from typing import Any

from core.governance.l3.meta_meta.types import BoundaryDefinition, LayerDefinition


class MetaLayerObserver:
    """Orchestrate L3-G5 meta-governance topology metrics (no execution)."""

    def run(
        self,
        layers: list[LayerDefinition],
        boundaries: list[BoundaryDefinition],
        ontology_drift_index: float,
        *,
        boundary_consistency: float,
    ) -> dict[str, float]:
        stability = 1.0 / (1.0 + ontology_drift_index)
        depth = float(len(layers))

        recursive_boundaries = sum(1 for b in boundaries if b.boundary_type == "recursive")
        if recursive_boundaries >= 2:
            stability *= max(0.5, 1.0 - recursive_boundaries * 0.08)

        return {
            "layer_system_stability": round(min(1.0, stability), 4),
            "boundary_consistency": round(boundary_consistency, 4),
            "ontology_drift_index": round(ontology_drift_index, 4),
            "self_referential_depth": round(depth, 4),
        }

    def classify(self, metrics: dict[str, float]) -> str:
        if metrics["ontology_drift_index"] > 0.7:
            return "unstable_meta_structure"
        if metrics["layer_system_stability"] < 0.3:
            return "fragmenting_governance"
        if metrics["self_referential_depth"] >= 7 and metrics["boundary_consistency"] >= 0.7:
            return "stable_meta_governance"
        if metrics["ontology_drift_index"] > 0.45:
            return "metastable_meta_governance"
        return "stable_meta_governance"


MetaLayerEngine = MetaLayerObserver  # deprecated v1 alias
