"""P3-B reliability: atomic IO, backup/restore, CDG ordering."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime
from memory.atomic_io import atomic_write_json
from memory.block_store import MemoryBlockStore
from memory.runtime_guard import runtime_write_context
from scripts import backup_memory, restore_memory


class TestAtomicBlockWrites(unittest.TestCase):
    def test_atomic_write_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "data.json"
            atomic_write_json(path, {"a": 1, "b": "测试"})
            loaded = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["a"], 1)
            self.assertEqual(loaded["b"], "测试")

    def test_block_store_uses_atomic_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryBlockStore(tmp)
            with runtime_write_context():
                store.create_block("episodic_event", "atomic write test content")
                block = store.update_block("episodic_event", "atomic write test content")
            raw = (Path(tmp) / f"{block.block_id}.json").read_text(encoding="utf-8")
            self.assertIn("atomic write test content", raw)
            index = json.loads((Path(tmp) / "index.json").read_text(encoding="utf-8"))
            self.assertIn(block.block_id, index)


class TestBackupRestore(unittest.TestCase):
    def test_backup_restore_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            project.mkdir()
            memory_dir = project / "memory"
            memory_dir.mkdir()
            (memory_dir / "blocks").mkdir()
            (memory_dir / "blocks" / "index.json").write_text("{}", encoding="utf-8")
            (memory_dir / "marker.txt").write_text("keep", encoding="utf-8")

            backup_report = backup_memory.backup(
                project_root=project,
                dest=Path(tmp) / "backups",
                memory_dir=str(memory_dir),
            )
            backup_dir = Path(backup_report["backup_dir"])
            self.assertTrue((backup_dir / "backup_manifest.json").exists())

            target_memory = project / "memory_restored"
            restore_report = restore_memory.restore(
                backup_dir=backup_dir,
                project_root=project,
                memory_dir=str(target_memory),
            )
            self.assertTrue((Path(restore_report["restored_to"]) / "marker.txt").exists())


class TestCdgBeforeMutations(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir)

    def test_cdg_reject_skips_narrative_mutation(self):
        timeline_before = len(self.runtime.narrative.narrative.key_milestones)
        expectations_before = dict(self.runtime.self_model.self_expectations)

        with patch.object(self.runtime, "_run_cdg_cycle") as mock_cdg:
            mock_cdg.return_value = {
                "approved": False,
                "reason": "SINGULARITY_BLOCK",
                "safe_response": "blocked",
                "rcs": 0.1,
            }
            result = self.runtime.process_interaction(
                "我的长期身份目标是维护连续性与稳定",
                assistant_output="收到，我会继续维护连续性。",
                use_memory=False,
            )

        self.assertFalse(result["ok"])
        self.assertEqual(len(self.runtime.narrative.narrative.key_milestones), timeline_before)
        self.assertEqual(self.runtime.self_model.self_expectations, expectations_before)


if __name__ == "__main__":
    unittest.main()
