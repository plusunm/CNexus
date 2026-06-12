import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.block import MemoryBlock
from memory.lifecycle import BlockLifecycleManager, MemoryManagementConfig
from memory.manager import MemoryManager


class TestBlockLifecycleManager(unittest.TestCase):
    def setUp(self):
        cfg = MemoryManagementConfig(
            block_forget_decay_threshold=0.15,
            block_min_effective_retain=0.20,
            max_archival_blocks=2,
            archival_compress_chars=100,
        )
        self.lifecycle = BlockLifecycleManager(cfg)

    def test_core_persona_protected_from_decay(self):
        block = MemoryBlock.from_label("persona", "稳定、理性、工程优先")
        block.last_accessed_at = datetime.now() - timedelta(days=30)
        block.decay_factor = 1.0
        updated = self.lifecycle.apply_decay(block)
        self.assertEqual(updated.decay_factor, 1.0)
        self.assertFalse(self.lifecycle.should_forget(updated))

    def test_working_memory_decays_when_idle(self):
        block = MemoryBlock.from_label("working_memory", "正在实现 L1 生命周期管理")
        block.protected = False
        block.decay_factor = 0.6
        block.decay_rate = 0.02
        block.last_accessed_at = datetime.now() - timedelta(days=10)
        updated = self.lifecycle.apply_decay(block)
        self.assertLess(updated.decay_factor, 0.6)

    def test_should_forget_weak_archival(self):
        block = MemoryBlock.from_label("archival_facts", "低重要性历史事实", importance=0.3)
        block.protected = False
        block.decay_factor = 0.1
        self.assertTrue(self.lifecycle.should_forget(block))

    def test_compress_archival_truncates_long_content(self):
        long_content = "\n".join(f"fact line {i} with some detail" for i in range(50))
        block = MemoryBlock.from_label("archival_facts", long_content)
        updated, count = self.lifecycle.compress_archival([block])
        self.assertEqual(count, 1)
        self.assertLess(len(updated[0].content), len(long_content))

    def test_compress_archival_merges_excess_blocks(self):
        blocks = [
            MemoryBlock.from_label("archival_facts", f"archival fact number {i}")
            for i in range(5)
        ]
        updated, count = self.lifecycle.compress_archival(blocks)
        archival = [b for b in updated if b.label == "archival_facts" and b.active]
        self.assertLessEqual(len(archival), 2)
        self.assertGreaterEqual(count, 3)


class TestMemoryManagerLifecycle(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.manager = MemoryManager(self._tmpdir, storage=None)

    def test_protect_block(self):
        self.manager.create_block("emotion", "情绪平稳，专注协作")
        protected = self.manager.protect_block("emotion")
        self.assertTrue(protected.protected)
        active = self.manager.get_active_block("emotion", touch=False)
        self.assertTrue(active.protected)

    def test_run_maintenance_decays_working_memory(self):
        block = self.manager.create_block("working_memory", "当前任务：实现 block 生命周期")
        block.protected = False
        block.decay_factor = 0.5
        block.decay_rate = 0.05
        block.last_accessed_at = datetime.now() - timedelta(days=14)
        self.manager.blocks.save(block)

        report = self.manager.run_maintenance(force=True)
        self.assertGreaterEqual(report["blocks"]["decayed"], 0)
        updated = self.manager.get_active_block("working_memory", touch=False)
        self.assertIsNotNone(updated)
        self.assertLess(updated.decay_factor, 0.5)

    def test_run_maintenance_never_forgets_persona(self):
        self.manager.create_block("persona", "稳定、理性、长期主义认知伙伴")
        report = self.manager.run_maintenance(force=True)
        self.assertGreaterEqual(report["blocks"]["protected"], 1)
        self.assertIsNotNone(self.manager.get_active_block("persona", touch=False))

    def test_compress_archival_blocks_via_manager(self):
        self.manager.block_lifecycle.config.max_archival_blocks = 2
        for i in range(4):
            self.manager.create_block("archival_facts", f"独立归档事实条目 {i} 的内容")
        result = self.manager.compress_archival_blocks()
        self.assertGreaterEqual(result["compressed"], 1)
        remaining = self.manager.blocks.list_archival_blocks()
        self.assertLessEqual(len(remaining), 2)


class TestRuntimeMaintainMemory(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def test_maintain_memory_runs_block_and_episodic(self):
        from brain_memory import BrainMemoryRuntime

        runtime = BrainMemoryRuntime(base_dir="memory", project_root=self._tmpdir)
        runtime.memory.create_block("working_memory", "当前任务：维护记忆生命周期")
        report = runtime.maintain_memory(force=True)
        self.assertIn("blocks", report)
        self.assertIn("episodic", report)
        self.assertIn("sleep_time", report)


if __name__ == "__main__":
    unittest.main()
