import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.personality.belief.belief_engine import BeliefEngine
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder


class TestBeliefGovernance(unittest.TestCase):
    def test_belief_governance(self):
        dna = PersonalityDNAEngine()
        narrative = NarrativeBuilder(dna)
        engine = BeliefEngine(dna, narrative)

        engine.add_or_update_belief("本地优先", 0.9)
        self.assertEqual(len(engine.graph.beliefs), 1)
        key = list(engine.graph.beliefs.keys())[0]
        self.assertGreater(engine.graph.beliefs[key].confidence, 0.8)


if __name__ == "__main__":
    unittest.main()
