import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime
from memory.runtime_guard import runtime_write_context


class TestAttentionPromptDiff(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir, project_root=root)

    def test_attention_changes_recall_ranking(self):
        with runtime_write_context():
            self.runtime.memory.create_block("persona", "稳定、理性、长期主义的人格设定")
            self.runtime.memory.create_block("intent", "推进认知系统架构落地与验证")

        query = "人格与长期目标"
        self.runtime.recall_pipeline.recall(query, use_attention=False)
        explain_off = dict(self.runtime.recall_pipeline.last_explain)

        self.runtime.recall_pipeline.recall(query, use_attention=True)
        explain_on = dict(self.runtime.recall_pipeline.last_explain)

        self.assertTrue(explain_on.get("use_attention"))
        self.assertFalse(explain_off.get("use_attention"))
        ranking_on = explain_on.get("ranking") or []
        self.assertTrue(
            any(r.get("attention_boost") for r in ranking_on)
            or bool(explain_on.get("attention_focus"))
        )

    def test_attention_changes_context_length_or_focus(self):
        with runtime_write_context():
            self.runtime.memory.create_block("emotion", "当前情绪专注协作与稳定输出")
        q = "当前情绪与协作状态"
        ctx_off = self.runtime.recall(q, use_attention=False)
        ctx_on = self.runtime.recall(q, use_attention=True)
        self.assertNotEqual(ctx_off, ctx_on)


if __name__ == "__main__":
    unittest.main()
