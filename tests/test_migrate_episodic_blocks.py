import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.migrate_episodic_blocks import _row_user_id, migrate


class TestMigrateEpisodicBlocks(unittest.TestCase):
    def test_row_user_id_from_metadata(self):
        row = {"metadata": {"user_id": "u1"}, "content": "hello"}
        self.assertEqual(_row_user_id(row), "u1")

    def test_dry_run_default_counts_without_writes(self):
        runtime = MagicMock()
        runtime.storage.vector.scan_memories.return_value = [
            {
                "layer": "episodic",
                "role": "user",
                "content": "test",
                "memory_id": "m1",
            }
        ]
        runtime.memory_manager._infer_episodic_type.return_value = "dialogue"

        report = migrate(runtime, dry_run=True, user_id=None)
        self.assertTrue(report["dry_run"])
        self.assertEqual(report["migrated"], 1)
        runtime.memory_manager.append_episodic_entry.assert_not_called()

    def test_user_id_filter(self):
        runtime = MagicMock()
        runtime.storage.vector.scan_memories.return_value = [
            {"layer": "episodic", "role": "user", "content": "a", "memory_id": "1", "user_id": "u1"},
            {"layer": "episodic", "role": "user", "content": "b", "memory_id": "2", "user_id": "u2"},
        ]
        runtime.memory_manager._infer_episodic_type.return_value = "dialogue"

        report = migrate(runtime, dry_run=True, user_id="u1")
        self.assertEqual(report["migrated"], 1)
        self.assertEqual(report["user_filtered"], 1)


if __name__ == "__main__":
    unittest.main()
