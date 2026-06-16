"""Tests for hidden Windows subprocess helpers."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.windows_subprocess import pids_listening_on_port


class TestWindowsSubprocess(unittest.TestCase):
    def test_parse_netstat_listening_pids(self) -> None:
        sample = """
Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       4242
  TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       4242
  TCP    0.0.0.0:11434          0.0.0.0:0              LISTENING       9999
"""
        with patch(
            "core.windows_subprocess.check_output_hidden",
            return_value=sample,
        ):
            pids = pids_listening_on_port(8000)
        self.assertEqual(pids, [4242])

    def test_hidden_kwargs_present_on_windows(self) -> None:
        from core.windows_subprocess import hidden_subprocess_kwargs

        kwargs = hidden_subprocess_kwargs()
        if sys.platform == "win32":
            self.assertIn("creationflags", kwargs)
            self.assertIn("startupinfo", kwargs)
        else:
            self.assertEqual(kwargs, {})


if __name__ == "__main__":
    unittest.main()
