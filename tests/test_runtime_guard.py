import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.manager import MemoryManager
from memory.runtime_guard import RuntimeViolationError, runtime_write_context


class TestRuntimeWriteGuard(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.manager = MemoryManager(self._tmpdir, storage=None)

    def test_direct_write_blocked(self):
        with self.assertRaises(RuntimeViolationError):
            self.manager.create_block("persona", "direct write")

    def test_runtime_context_allows_write(self):
        with runtime_write_context():
            block = self.manager.create_block("persona", "authorized write")
        self.assertEqual(block.label, "persona")

    def test_bypass_flag_allows_write(self):
        mgr = MemoryManager(self._tmpdir, storage=None, bypass_runtime_guard=True)
        block = mgr.create_block("emotion", "bypass ok")
        self.assertEqual(block.label, "emotion")


if __name__ == "__main__":
    unittest.main()
