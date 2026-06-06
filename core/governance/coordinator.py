from core.governance.drift_detector import DriftDetector
from core.governance.identity_anchoring import IdentityAnchorManager
from core.governance.stability_types import StabilityMetrics
from core.personality.belief.belief_engine import BeliefEngine
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder


class StabilityCoordinator:
    """Stability Governance 总控"""

    def __init__(
        self,
        dna: PersonalityDNAEngine,
        narrative: NarrativeBuilder,
        belief: BeliefEngine,
    ):
        self.detector = DriftDetector(dna, narrative, belief)
        self.anchoring = IdentityAnchorManager(dna, narrative)
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

        self.metrics.overall_stability_score = max(0.3, 1.0 - drift_report.drift_score * 0.7)
        self.metrics.narrative_coherence = self.anchoring.narrative.narrative.narrative_coherence_score

        return {
            "drift_report": drift_report.model_dump(),
            "anchor_context": anchor_context,
            "stability_metrics": self.metrics.model_dump(),
        }
