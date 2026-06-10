"""L7 — Dual-track causal transition validator (v2.3.1)."""

from __future__ import annotations

from typing import Any, Dict, List

from core.governance.l7.transition_reconstructor import (
    StateTransition,
    TransitionOperator,
    TransitionReconstructor,
)


class CausalTransitionValidator:
    """
    Dual-track transition legality:

    - structural: TransitionReconstructor + operator/delta constraints
    - behavioral: grounding_diff + intervention exemption (v2.2 fusion)
    - combined:   0.55 * structural + 0.45 * behavioral
    """

    MAX_GROUNDING_DROP = 0.15
    MAX_GROUNDING_DIFF = 0.18
    MAX_V_SPIKE = 0.30
    STRUCTURAL_WEIGHT = 0.55
    BEHAVIORAL_WEIGHT = 0.45

    def __init__(self) -> None:
        self.reconstructor = TransitionReconstructor()

    def validate_transition(self, transition: StateTransition) -> float:
        score = transition.legality_score

        s_t, s_next = transition.s_t, transition.s_next
        g_drop = float(s_t.get("grounding_avg") or 0) - float(s_next.get("grounding_avg") or 0)
        if s_next.get("approved") and g_drop > self.MAX_GROUNDING_DROP:
            score *= 0.5

        v_jump = transition.state_next.potential_v - transition.state_t.potential_v
        if v_jump > self.MAX_V_SPIKE and s_next.get("approved"):
            if transition.operator != TransitionOperator.CONTROL:
                score *= 0.4

        return max(0.0, min(1.0, score))

    @classmethod
    def behavioral_pair(cls, s_t: Dict[str, Any], s_next: Dict[str, Any]) -> float:
        diff = abs(
            float(s_next.get("grounding_avg") or 0) - float(s_t.get("grounding_avg") or 0)
        )
        has_intervention = bool(s_next.get("interventions"))
        if diff > cls.MAX_GROUNDING_DIFF and not has_intervention:
            return 0.0
        return 1.0

    @classmethod
    def behavioral_legality(cls, records: List[Dict[str, Any]]) -> float:
        if len(records) < 2:
            return 1.0
        scores = [
            cls.behavioral_pair(records[i], records[i + 1]) for i in range(len(records) - 1)
        ]
        return sum(scores) / len(scores)

    @classmethod
    def combine_legality(cls, structural: float, behavioral: float) -> float:
        return max(
            0.0,
            min(
                1.0,
                cls.STRUCTURAL_WEIGHT * structural + cls.BEHAVIORAL_WEIGHT * behavioral,
            ),
        )

    def analyze(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        transitions = self.reconstructor.build(records)
        behavioral = self.behavioral_legality(records)

        if not transitions:
            structural = 1.0
            combined = self.combine_legality(structural, behavioral)
            return {
                "transition_count": 0,
                "structural_legality": structural,
                "behavioral_legality": behavioral,
                "transition_legality": combined,
                "causal_consistency": self.structural_consistency(records),
                "transition_violations": 0,
                "operators": {},
            }

        structural_scores = [self.validate_transition(t) for t in transitions]
        structural = sum(structural_scores) / len(structural_scores)
        combined = self.combine_legality(structural, behavioral)
        violation_count = sum(1 for t in transitions if t.violations)

        op_counts: Dict[str, int] = {}
        for t in transitions:
            op_counts[t.operator.value] = op_counts.get(t.operator.value, 0) + 1

        return {
            "transition_count": len(transitions),
            "structural_legality": structural,
            "behavioral_legality": behavioral,
            "transition_legality": combined,
            "causal_consistency": self.structural_consistency(records),
            "transition_violations": violation_count,
            "operators": op_counts,
            "transitions": transitions,
        }

    @classmethod
    def allows(cls, prev: Dict[str, Any], curr: Dict[str, Any]) -> bool:
        t = TransitionReconstructor()._pair(0, prev, curr)
        structural = CausalTransitionValidator().validate_transition(t)
        behavioral = cls.behavioral_pair(prev, curr)
        return cls.combine_legality(structural, behavioral) >= 0.75

    @classmethod
    def transition_legality(cls, records: List[Dict[str, Any]]) -> float:
        return CausalTransitionValidator().analyze(records)["transition_legality"]

    @classmethod
    def structural_consistency(cls, records: List[Dict[str, Any]], *, window: int = 40) -> float:
        if not records:
            return 0.0
        slice_ = records[-window:]
        reconstructor = TransitionReconstructor()
        transitions = reconstructor.build(slice_)
        if not transitions:
            tip_ratio = sum(1 for r in slice_ if r.get("reality_tip")) / max(len(slice_), 1)
            return tip_ratio * 0.8

        struct_ok = sum(1 for t in transitions if t.hash_evolution_valid and t.tip_chain_valid)
        return struct_ok / len(transitions)
