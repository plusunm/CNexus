import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.filter import CaptureFilter, CaptureMode


class TestMemoryFilter(unittest.TestCase):
    def test_reject_short(self):
        rejected, _ = CaptureFilter.should_reject("user", "hi", mode=CaptureMode.CHAT)
        self.assertTrue(rejected)

    def test_accept_valid(self):
        rejected, _ = CaptureFilter.should_reject(
            "user", "我希望长期构建稳定的人格 AI 系统", mode=CaptureMode.CHAT
        )
        self.assertFalse(rejected)


if __name__ == "__main__":
    unittest.main()
