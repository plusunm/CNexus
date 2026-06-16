from typing import Optional

from core.governance.drift_detector import DriftSignalExtractor
from core.governance.identity_anchoring import IdentityAnchorRegistry
from core.governance.stability_types import StabilityMetrics
from core.personality.belief.belief_engine import BeliefEngine
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder
from core.personality.reflective.reflection_pipeline import ReflectionPipeline


class StabilityCoordinator:
    """Stability Governance 总控 — 统一注入 Personality 全链路"""

    def __init__(
        self,
        dna: PersonalityDNAEngine,
        narrative: NarrativeBuilder,
        belief: BeliefEngine,
        reflection: Optional[ReflectionPipeline] = None,
        state_manager=None,
    ):
        self.dna = dna
        self.narrative = narrative
        self.belief = belief
        self.reflection = reflection
        self.state_manager = state_manager
        self.detector = DriftSignalExtractor(dna, narrative, belief, reflection)
        self.anchoring = IdentityAnchorRegistry(dna, narrative)
        self.metrics = StabilityMetrics(
            identity_stability=0.92,
            narrative_coherence=0.88,
            belief_consistency=0.85,
            personality_integrity=0.90,
            cognitive_load=0.45,
            entropy_level=0.32,
            overall_stability_score=0.87,
        )

    def run_governance_cycle(self):
        drift_report = self.detector.detect()
        anchor_context = self.anchoring.generate_anchor_context()

        if self.state_manager:
            sm = self.state_manager.get_stability_metrics()
            self.metrics.cognitive_load = sm.get("cognitive_load", self.metrics.cognitive_load)
            self.metrics.entropy_level = sm.get("attention_entropy", self.metrics.entropy_level)
            self.metrics.identity_stability = sm.get("identity_stability", self.metrics.identity_stability)

        self.metrics.overall_stability_score = max(0.3, 1.0 - drift_report.drift_score * 0.7)
        self.metrics.narrative_coherence = self.narrative.narrative.narrative_coherence_score
        self.metrics.belief_consistency = min(
            1.0, len(self.belief.get_active_beliefs(min_confidence=0.6)) / max(1, len(self.belief.graph.beliefs))
        )

        result = {
            "drift_report": drift_report.model_dump(),
            "anchor_context": anchor_context,
            "stability_metrics": self.metrics.model_dump(),
        }
        if self.reflection:
            result["reflection_summary"] = {
                "active": len(self.reflection.get_active_reflections()),
                "due_reviews": self.reflection.count_due_reviews(),
            }
        return result
