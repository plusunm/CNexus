"""Semantic Safety v5 — interpretation isolation orchestrator."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from core.governance.semantic_safety.v5.interpretation_fragmenter import InterpretationFragmenter
from core.governance.semantic_safety.v5.interpretation_space import InterpretationSpace
from core.governance.semantic_safety.v5.meaning_erosion_layer import MeaningErosionLayer
from core.governance.semantic_safety.v5.non_coherence_mapper import NonCoherenceMapper
from core.governance.semantic_safety.v5.observer_model_shield import ObserverModelShield
from core.governance.semantic_safety.v5.semantic_decomposition import SemanticDecomposer


@dataclass
class IsolationResult:
    output: dict[str, Any]
    isolation_status: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**self.output, "isolation_status": self.isolation_status}


class InterpretationIsolationLayer:
    """
    Cut stable output → governance-interpretation mapping paths.
    Does not mutate runtime or stored observational records.
    """

    def __init__(self) -> None:
        self._space = InterpretationSpace()
        self._decomposer = SemanticDecomposer()
        self._fragmenter = InterpretationFragmenter()
        self._erosion = MeaningErosionLayer()
        self._mapper = NonCoherenceMapper()
        self._shield = ObserverModelShield()

    def isolate(self, presentation_output: dict[str, Any]) -> IsolationResult:
        field_data = presentation_output.get("data", presentation_output)
        space = self._space.project(field_data)
        blocks = self._decomposer.decompose(field_data)
        fragments = self._fragmenter.fragment(blocks)
        eroded = self._erosion.erode(fragments)
        meaning_state = self._erosion.summarize(eroded)
        non_coherence = self._mapper.map(blocks)
        observer = self._shield.isolate(presentation_output)

        semantic_fragments = [
            {
                "token": f["fragment"].get("token", ""),
                "interpretability": f.get("interpretability", "partial"),
                "connectivity": f.get("connectivity", "broken"),
            }
            for f in eroded[:24]
        ]

        result = {
            "interpretation_isolation_v5": True,
            "interpretation_space": {
                "coherence": space["coherence"],
                "stability": space["interpretation_stability"],
                "governance_projection": space["governance_projection_possible"],
            },
            "semantic_fragments": semantic_fragments,
            "non_coherence_map": non_coherence,
            "meaning_state": meaning_state,
            "observer_model": observer,
            "system_note": "output cannot be reliably interpreted as control or governance signal",
            "presentation_envelope": copy.deepcopy(presentation_output),
            "semantic_safety_version": "5.0.0",
        }

        status = {
            "fragment_count": len(eroded),
            "coherence": space["coherence"],
            "governance_projection_blocked": not space["governance_projection_possible"],
            "isolation_pass": True,
        }
        return IsolationResult(output=result, isolation_status=status)


def apply_interpretation_isolation(
    payload: dict[str, Any],
    *,
    through_v4: bool = True,
) -> dict[str, Any]:
    """Apply v5 isolation; optionally chain through v4 firewall first."""
    if through_v4:
        from core.governance.semantic_safety.v4 import apply_semantic_firewall

        payload = apply_semantic_firewall(payload)
    return InterpretationIsolationLayer().isolate(payload).to_dict()
