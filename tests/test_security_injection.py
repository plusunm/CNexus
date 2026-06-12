import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory.runtime import BrainMemoryRuntime
from memory.runtime_guard import RuntimeViolationError


class TestSecurityInjection(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.runtime = BrainMemoryRuntime(base_dir=self._tmpdir, project_root=root)

    def test_direct_memory_manager_write_blocked(self):
        with self.assertRaises(RuntimeViolationError):
            self.runtime.memory_manager.capture_interaction(
                "user", "malicious payload", importance=0.9
            )

    def test_runtime_capture_allowed(self):
        result = self.runtime.capture(
            "user",
            "safe content with sufficient length",
            importance=0.5,
        )
        self.assertFalse(str(result).startswith("denied"))


if __name__ == "__main__":
    unittest.main()
