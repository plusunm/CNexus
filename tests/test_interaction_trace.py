"""Interaction step trace — minimal Σ.T slice for process_interaction."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInteractionTrace(unittest.TestCase):
    def test_process_interaction_emits_trace_steps(self):
        from brain_memory import BrainMemoryRuntime
        from core.runtime.execution_trace import trace_file_path

        root = tempfile.mkdtemp(prefix="cnexus-trace-")
        runtime = BrainMemoryRuntime(base_dir=root, project_root=root)
        runtime.process_interaction(
            message="hello trace",
            use_memory=False,
            chat_mode=True,
            assistant_output="pong",
        )
        path = trace_file_path(str(runtime.base_dir))
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        steps = [row.get("step") for row in rows if row.get("type") == "interaction_step"]
        self.assertIn("cdg_ingest", steps)
        self.assertIn("capture_user", steps)
        self.assertIn("complete", steps)


if __name__ == "__main__":
    unittest.main()
