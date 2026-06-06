import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder


class TestNarrativeContinuity(unittest.TestCase):
    def test_narrative_continuity(self):
        dna = PersonalityDNAEngine()
        builder = NarrativeBuilder(dna)

        builder.update_from_memory("长期目标是维护身份连续性", 0.9)
        self.assertGreater(len(builder.narrative.long_term_goals), 0)
        self.assertGreater(builder.narrative.narrative_coherence_score, 0.7)


if __name__ == "__main__":
    unittest.main()
