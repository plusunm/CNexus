"""CSE engine tests."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cse.engine import CognitiveSynthesisEngine
from core.cse.snapshot import SynthesisSnapshotStore, get_snapshot_store


class TestCognitiveSynthesisEngine(unittest.TestCase):
    def setUp(self):
        store = get_snapshot_store()
        store._archive.clear()

    def _run(self, engine, **kwargs):
        defaults = dict(
            runtime=type(
                "R",
                (),
                {"config": {"runtime_envelope": "safe_baseline", "cse_mode": "batch"}},
            )(),
            logs=[
                {"category": "chat", "level": "info", "message": "ok"},
                {"category": "execution", "level": "info", "message": "boot"},
            ],
            execution_status={
                "runtime_envelope": "safe_baseline",
                "inference_scheduler": {
                    "enabled": True,
                    "max_concurrent": 1,
                    "embed_strategy": "serial",
                    "cache_hits": 8,
                    "cache_misses": 2,
                },
                "compute_profile": {"ram_gb": 16, "gpu": False, "cpu_cores": 8},
                "embedding": {"active_mode": "hash"},
            },
            mind_overview={
                "system": {"health_label": "stable", "governance_label": "observe"},
                "feeds": {"changes": ["goal layer updated"]},
            },
            window=50,
        )
        defaults.update(kwargs)
        return engine.synthesize_live(**defaults)

    def test_synthesizes_from_scheduler_signals(self):
        engine = CognitiveSynthesisEngine()
        output = self._run(engine)
        self.assertTrue(output.summary)
        self.assertTrue(output.patterns)
        self.assertTrue(output.actions)
        self.assertTrue(output.narrative)
        self.assertTrue(output.experiences)
        payload = output.to_dict()
        self.assertIn("insights", payload)
        self.assertIn("discoveries", payload)
        self.assertGreaterEqual(len(payload["actions"]), 1)

    def test_novelty_diff_on_second_synthesis(self):
        engine = CognitiveSynthesisEngine()
        first = self._run(engine)
        self.assertTrue(first.discoveries or first.insights)

        second = self._run(
            engine,
            logs=[
                {"category": "chat", "level": "info", "message": "ok"},
                {"category": "embed", "level": "error", "message": "new failure mode"},
            ],
        )
        self.assertTrue(second.narrative)
        has_error_summary = any("error" in s.text.lower() for s in second.summary)
        self.assertTrue(has_error_summary or second.discoveries or second.insights)

    def test_snapshot_store_archive(self):
        store = SynthesisSnapshotStore()
        engine = CognitiveSynthesisEngine()
        out = self._run(engine)
        store.commit(out)
        self.assertEqual(len(store.list_archive()), 1)
        self.assertTrue(store.last_fingerprint())


if __name__ == "__main__":
    unittest.main()
