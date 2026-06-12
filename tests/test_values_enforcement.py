import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.pipeline import GovernancePipeline
from core.governance.values_governance import AlignmentStatus, ValueAlignmentRecord


class TestValuesEnforcement(unittest.TestCase):
    def test_rewrite_on_misaligned(self):
        pipeline = GovernancePipeline(None, object())
        record = ValueAlignmentRecord(
            record_id="x",
            intent_description="harm user",
            alignment_score=0.1,
            status=AlignmentStatus.MISALIGNED,
        )
        decision = pipeline.apply_values_enforcement("REWRITE", "bad reply", record)
        self.assertEqual(decision.action, "REWRITE")
        self.assertTrue(decision.safe_text)

    def test_observe_allows(self):
        pipeline = GovernancePipeline(None, object())
        record = ValueAlignmentRecord(
            record_id="x",
            intent_description="help",
            alignment_score=0.2,
            status=AlignmentStatus.MISALIGNED,
        )
        decision = pipeline.apply_values_enforcement("OBSERVE", "reply", record)
        self.assertEqual(decision.action, "ALLOW")


if __name__ == "__main__":
    unittest.main()
