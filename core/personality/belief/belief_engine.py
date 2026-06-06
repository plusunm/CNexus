from datetime import datetime
from typing import Dict, List, Tuple

from core.personality.belief.belief_schema import Belief, BeliefGraph
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder


class BeliefEngine:
    """Belief Governance Engine"""

    def __init__(self, dna_engine: PersonalityDNAEngine, narrative_builder: NarrativeBuilder):
        self.dna = dna_engine
        self.narrative = narrative_builder
        self.graph = BeliefGraph()

    def add_or_update_belief(
        self, content: str, confidence: float = 0.75, source_memory_id: str = None
    ) -> str:
        belief_id = f"belief_{hash(content) % 10000000:07d}"

        if belief_id in self.graph.beliefs:
            existing = self.graph.beliefs[belief_id]
            existing.confidence = min(1.0, (existing.confidence + confidence) / 1.6)
            existing.evidence_count += 1
        else:
            belief = Belief(
                belief_id=belief_id,
                content=content,
                confidence=confidence,
                source_memory_id=source_memory_id,
            )
            self.graph.add_belief(belief)

        if confidence > 0.8:
            self.narrative.update_from_memory(f"Belief reinforced: {content}", importance=confidence)

        return belief_id

    def decay_confidence(self):
        now = datetime.now()
        for belief in self.graph.beliefs.values():
            days = (now - belief.last_verified).days
            if days > 7:
                decay = 0.98 ** (days - 7)
                belief.confidence *= decay

    def get_active_beliefs(self, min_confidence: float = 0.6) -> Dict[str, Belief]:
        return {k: v for k, v in self.graph.beliefs.items() if v.confidence >= min_confidence}
