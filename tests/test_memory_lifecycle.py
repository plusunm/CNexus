import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.lifecycle import MemoryLifecycleManager, MemoryManagementConfig
from storage.manager import UnifiedStorageManager


class TestMemoryLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = UnifiedStorageManager(base_dir=self.tmp.name, vector_dim=768)
        self._embed = [0.01] * 768
        cfg = MemoryManagementConfig(
            max_total_memories=3,
            max_per_layer={"episodic": 2},
            recall_access_cap=5,
            forget_decay_threshold=0.2,
            min_importance_retain=0.3,
            stale_days=0,
        )
        self.lifecycle = MemoryLifecycleManager(self.storage, cfg)
        self.storage.configure_lifecycle(self.lifecycle)
        self.storage.set_recall_access_cap(cfg.recall_access_cap)

    def tearDown(self):
        self.tmp.cleanup()

    def _seed(self, content: str, importance: float = 0.4, layer: str = "episodic", decay: float = 0.1):
        return self.storage.capture_memory(
            role="user",
            content=content,
            layer=layer,
            importance=importance,
            embedding=self._embed,
            decay_factor=decay,
        )

    def test_recall_access_cap(self):
        mid = self._seed("low importance episodic memory one", importance=0.4)
        for _ in range(8):
            self.storage.recall("memory", top_k=1)
        rows = self.storage.vector.scan_memories()
        row = next(r for r in rows if r["memory_id"] == mid)
        self.assertLessEqual(int(row["access_count"]), 5)

    def test_forget_low_decay(self):
        self._seed("forgettable low decay trace", importance=0.25, decay=0.08)
        report = self.lifecycle.run_maintenance(force=True)
        self.assertGreaterEqual(report.forgotten, 1)

    def test_capacity_eviction(self):
        for i in range(5):
            self._seed(f"episodic filler memory item {i}", importance=0.35, decay=0.5)
        report = self.lifecycle.run_maintenance(force=True)
        stats = self.lifecycle.collect_stats()
        self.assertLessEqual(stats.total, 3)
        self.assertGreater(report.evicted_capacity, 0)

    def test_protected_identity_retained(self):
        self._seed("core identity anchor memory", importance=0.9, layer="identity", decay=0.5)
        for i in range(4):
            self._seed(f"episodic filler {i}", importance=0.35, decay=0.5)
        self.lifecycle.run_maintenance(force=True)
        rows = self.storage.vector.scan_memories()
        layers = {r["layer"] for r in rows}
        self.assertIn("identity", layers)


if __name__ == "__main__":
    unittest.main()
