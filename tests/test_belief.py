import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.personality.belief.belief_engine import BeliefEngine
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder


def test_belief_governance():
    dna = PersonalityDNAEngine()
    narrative = NarrativeBuilder(dna)
    engine = BeliefEngine(dna, narrative)

    engine.add_or_update_belief("本地优先", 0.9)
    assert len(engine.graph.beliefs) == 1
    key = list(engine.graph.beliefs.keys())[0]
    assert engine.graph.beliefs[key].confidence > 0.8
