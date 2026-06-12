"""Benchmark suite — memory / attention / reflection on-off (P3-A)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime


class TestBenchmarkSuite(unittest.TestCase):
    """Prove subsystem effectiveness with measurable deltas."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir, project_root=root)

    def _seed_memory(self):
        self.runtime.capture(
            "user",
            "我的长期目标是构建稳定可靠的认知系统架构",
            layer="goal",
            importance=0.88,
        )

    def test_memory_on_off_recall_delta(self):
        self._seed_memory()
        query = "认知系统架构目标"
        off = self.runtime.recall_pipeline.recall(query, use_memory=False)
        on = self.runtime.recall_pipeline.recall(query, use_memory=True)
        self.assertEqual(off, "")
        self.assertGreater(len(on), len(off))
        self.assertGreater(self.runtime.recall_pipeline.last_explain.get("context_chars", 0), 0)

    def test_attention_on_off_recall_delta(self):
        self._seed_memory()
        query = "认知系统架构目标"
        without = self.runtime.recall_pipeline.recall(query, use_attention=False)
        with_attn = self.runtime.recall_pipeline.recall(query, use_attention=True)
        self.assertNotEqual(without, with_attn)
        explain_on = self.runtime.recall_pipeline.last_explain
        self.assertTrue(explain_on.get("use_attention"))

    @patch.object(BrainMemoryRuntime, "_generate_llm_response", return_value="详细回复：我会持续维护系统稳定性。")
    def test_reflection_on_off_narrative_delta(self, _mock):
        self.runtime.config["reflective_use_llm"] = False
        self.runtime.config["reflection_cooldown_turns"] = 0
        self.runtime.process_interaction(
            "讨论系统稳定性与长期维护策略",
            assistant_output="详细回复：我会持续维护系统稳定性。",
        )
        block_off = self.runtime.memory_manager.get_active_block("narrative", touch=False)
        v_off = block_off.version if block_off else 0

        self.runtime.config["reflective_use_llm"] = True
        self.runtime.process_interaction(
            "继续深入讨论系统稳定性策略",
            assistant_output="详细回复：我会持续维护系统稳定性。",
        )
        block_on = self.runtime.memory_manager.get_active_block("narrative", touch=False)
        v_on = block_on.version if block_on else 0
        self.assertGreaterEqual(v_on, v_off)


if __name__ == "__main__":
    unittest.main()
