import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governance.values_governance import AlignmentStatus, ValuesGovernance
from core.memory.sleep_time_compute import SleepTimeCompute
from core.personality.emotion_engine import EmotionEngine
from core.personality.intent_engine import IntentEngine
from core.personality.reflective.reflective_engine import REFLECTIVE_LABEL, ReflectiveEngine
from memory.manager import MemoryManager


def _backdate_block(manager: MemoryManager, block_id: str, days: int) -> None:
    block = manager.get_block(block_id)
    assert block is not None
    old = datetime.now() - timedelta(days=days)
    block.created_at = old
    block.updated_at = old
    block.last_accessed_at = old
    manager.blocks.save(block)


class TestSleepTimeCompute(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.manager = MemoryManager(self._tmpdir, storage=None, bypass_runtime_guard=True)
        emotion = EmotionEngine(self.manager)
        intent = IntentEngine(self.manager)
        self.reflective = ReflectiveEngine(self.manager, emotion, intent)
        self.sleep = SleepTimeCompute(
            self.manager,
            reflective_engine=self.reflective,
            compression_threshold_days=7,
            min_batch_reflections=3,
        )

    def _create_reflective_block(self, reflection: str, *, days_old: int = 10) -> str:
        record = self.reflective.reflect_on_interaction(
            "assistant reply for sleep-time test",
            {"query": "test", "user_input": "test"},
        )
        blocks = self.manager.blocks.list_blocks(label=REFLECTIVE_LABEL)
        block_id = blocks[-1].block_id
        payload = json.loads(blocks[-1].content)
        payload["reflection"] = reflection
        self.manager.update_block(block_id, json.dumps(payload, ensure_ascii=False))
        _backdate_block(self.manager, block_id, days_old)
        return block_id

    def test_compress_reflective_trace(self):
        long_reflection = "反思内容" * 80
        block_id = self._create_reflective_block(long_reflection, days_old=10)
        report = self.sleep.run_sleep_cycle(force=False)
        self.assertGreaterEqual(report.reflective_compressed, 1)

        block = self.manager.get_block(block_id)
        self.assertIsNotNone(block)
        parsed = json.loads(block.content)
        self.assertTrue(parsed.get("compressed"))
        self.assertLessEqual(len(parsed.get("reflection", "")), 203)

    def test_compress_value_alignment_history(self):
        governance = ValuesGovernance(self.manager)
        record = governance.check_intent_alignment(
            "长期帮助用户",
            persona_values=["helpfulness", "long-term consistency"],
        )
        self.assertEqual(record.status, AlignmentStatus.ALIGNED)

        blocks = self.manager.blocks.list_blocks(label="value_alignment_history")
        block_id = blocks[0].block_id
        payload = json.loads(blocks[0].content)
        payload["alignment_score"] = 0.9
        payload["status"] = "aligned"
        self.manager.update_block(block_id, json.dumps(payload, ensure_ascii=False))
        _backdate_block(self.manager, block_id, days=20)

        report = self.sleep.run_sleep_cycle(force=False)
        self.assertGreaterEqual(report.value_alignment_compressed, 1)

        archived = self.manager.get_block(block_id)
        self.assertIsNotNone(archived)
        archived_payload = json.loads(archived.content)
        self.assertTrue(archived_payload.get("archived"))

    def test_batch_reflect_on_past(self):
        for idx in range(3):
            self._create_reflective_block(f"批量反思样本 {idx}", days_old=1)

        before = len(self.manager.blocks.list_blocks(label=REFLECTIVE_LABEL))
        report = self.sleep.run_sleep_cycle(force=True)
        after = len(self.manager.blocks.list_blocks(label=REFLECTIVE_LABEL))
        self.assertGreaterEqual(report.batch_reflections_generated, 3)
        self.assertGreater(after, before)

    def test_run_sleep_cycle_async(self):
        import asyncio

        self._create_reflective_block("异步测试反思", days_old=10)
        report = asyncio.run(self.sleep.run_sleep_cycle_async(force=False))
        self.assertGreaterEqual(report.reflective_compressed, 1)


class TestSleepTimeRuntimeIntegration(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_maintain_memory_includes_sleep_time(self):
        from brain_memory import BrainMemoryRuntime

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        runtime.process_interaction(
            "长期维护身份连续性",
            assistant_output="收到，继续维护稳定性。",
        )
        report = runtime.maintain_memory(force=True)
        self.assertIn("sleep_time", report)
        self.assertIn("blocks_processed", report["sleep_time"])


if __name__ == "__main__":
    unittest.main()
