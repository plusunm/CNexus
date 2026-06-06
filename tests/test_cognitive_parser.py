import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory import create_runtime
from runtime.cognitive_parser import CognitiveStateParser


class TestCognitiveParser(unittest.TestCase):
    def setUp(self):
        self.parser = CognitiveStateParser()

    def test_cache_avoids_reparse(self):
        a = self.parser.parse_cognitive_state("谢谢你的帮助，很务实")
        b = self.parser.parse_cognitive_state("谢谢你的帮助，很务实")
        self.assertTrue(b.cache_hit)
        self.assertFalse(a.used_llm)

    def test_belief_delta_capped(self):
        parsed = self.parser.parse_cognitive_state("务实稳定" * 20, importance=1.0)
        for delta in parsed.belief_delta.values():
            self.assertLessEqual(abs(delta), 0.08)

    def test_negative_relation_shift(self):
        parsed = self.parser.parse_cognitive_state("你真是垃圾，太失望了", importance=0.8)
        self.assertLess(parsed.relation_shift, 0)

    def test_dissonance_triggers_immediate_summary(self):
        tmp = tempfile.mkdtemp()
        rt = create_runtime(project_root=tmp, base_dir="memory")
        before = rt.narrative.narrative.identity_summary
        rt.parse_cognitive_state("你完全变了，不像之前那样，我很失望", importance=0.9)
        after = rt.narrative.narrative.identity_summary
        self.assertNotEqual(before, after)
        self.assertLess(rt.narrative.narrative.relationship_scores.get("user", 1.0), 0.55)

    def test_interval_summary_without_dissonance(self):
        tmp = tempfile.mkdtemp()
        rt = create_runtime(project_root=tmp, base_dir="memory")
        summaries = []
        for i in range(6):
            rt.parse_cognitive_state(f"普通消息 {i}", importance=0.3)
            summaries.append(rt.narrative.narrative.identity_summary)
        self.assertTrue(len(set(summaries)) >= 2)


if __name__ == "__main__":
    unittest.main()
