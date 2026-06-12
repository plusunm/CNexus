import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime


class TestE2ERuntime(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir, project_root=root)

    @patch.object(BrainMemoryRuntime, "_generate_llm_response", return_value="我会协助你完成详细的学习计划安排。")
    def test_capture_recall_reflect_loop(self, _mock_llm):
        r1 = self.runtime.process_interaction(
            "帮我制定一个详细的学习计划",
            assistant_output="我会协助你完成详细的学习计划安排。",
            use_memory=True,
        )
        self.assertTrue(r1.get("ok", True), msg=r1.get("reason"))
        self.assertIsNotNone(r1.get("capture_id"))

        context = self.runtime.recall("学习计划")
        self.assertIsInstance(context, str)

        r2 = self.runtime.process_interaction(
            "刚才我们聊了什么主题，请简要回顾",
            assistant_output="我们刚才在讨论详细的学习计划与执行步骤。",
            use_memory=True,
        )
        self.assertTrue(r2.get("ok", True), msg=r2.get("reason"))
        self.assertIn("context", r2)


if __name__ == "__main__":
    unittest.main()
