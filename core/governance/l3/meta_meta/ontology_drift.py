"""L3-G5 — governance ontology drift across recursion depth."""

from __future__ import annotations

from core.governance.l3.meta_meta.types import LayerDefinition, OntologyDrift

_PURPOSE_TOKENS = frozenset(
    {
        "interpret",
        "detect",
        "model",
        "simulate",
        "optimize",
        "reflect",
        "define",
        "observe",
        "shadow",
        "reflexivity",
        "meta",
    }
)


def _purpose_signature(purpose: str) -> set[str]:
    lower = purpose.lower()
    return {t for t in _PURPOSE_TOKENS if t in lower}


class OntologyDriftAnalyzer:
    """Measure how governance meaning shifts across layer depth."""

    def compute_drift(self, layers: list[LayerDefinition]) -> tuple[float, list[OntologyDrift]]:
        if len(layers) < 2:
            return 0.0, []

        drifts: list[OntologyDrift] = []
        total = 0.0

        for i in range(1, len(layers)):
            prev_sig = _purpose_signature(layers[i - 1].purpose)
            curr_sig = _purpose_signature(layers[i].purpose)
            union = prev_sig | curr_sig
            if not union:
                shift = 0.0
            else:
                shift = 1.0 - len(prev_sig & curr_sig) / len(union)

            depth_factor = i / max(len(layers) - 1, 1)
            score = min(1.0, shift * (0.5 + 0.5 * depth_factor))
            drifts.append(
                OntologyDrift(
                    layer_name=layers[i].name,
                    drift_score=round(score, 4),
                    semantic_shift=round(shift, 4),
                )
            )
            total += score

        index = total / (len(layers) - 1)
        return round(index, 4), drifts

    def adjust_index_from_g4(self, base_index: float, g4_payload: dict) -> float:
        """Supplement ontology index from G4 meta-governance state (observational)."""
        phase = g4_payload.get("meta_governance_state", "stable")
        bonus = {"drifting": 0.15, "self_sealing": 0.25, "expanding": 0.05}.get(phase, 0.0)
        reflexivity = float(g4_payload.get("reflexivity_score", 0))
        bonus += min(0.1, reflexivity * 0.1)
        return min(1.0, round(base_index + bonus, 4))
