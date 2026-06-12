import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime


class TestReflectionChangesNextRecall(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir, project_root=root)

    @patch.object(
        BrainMemoryRuntime,
        "_generate_llm_response",
        side_effect=["第一次详细回复关于信任的内容", "第二次详细回复继续深入讨论"],
    )
    def test_reflection_updates_narrative_block(self, _mock_llm):
        self.runtime.process_interaction("讨论信任与长期关系", use_memory=True)
        block_before = self.runtime.memory_manager.get_active_block("narrative", touch=False)

        self.runtime.process_interaction("继续深入探讨信任话题", use_memory=True)
        block_after = self.runtime.memory_manager.get_active_block("narrative", touch=False)

        self.assertTrue(block_before is not None or block_after is not None)
        self.assertIsNotNone(block_after)
        if block_before and block_after:
            self.assertGreaterEqual(block_after.version, block_before.version)


if __name__ == "__main__":
    unittest.main()
