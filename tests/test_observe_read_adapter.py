"""X3-b read_adapter normalization tests."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kernel.observe.read_adapter import normalize_memory_stats, observe_governance_state


class TestReadAdapter(unittest.TestCase):
    def test_normalize_memory_stats_from_dict(self) -> None:
        out = normalize_memory_stats(
            {
                "total": 5,
                "by_layer": {"episodic": 3},
                "avg_importance": 0.7,
                "avg_decay_factor": 0.9,
                "high_access_count": 1,
            }
        )
        self.assertEqual(out["total"], 5)
        self.assertEqual(out["by_layer"]["episodic"], 3)

    def test_observe_governance_state_via_callable(self) -> None:
        payload = observe_governance_state(lambda kind: {"governance_state": True, "kind": kind})
        self.assertTrue(payload.get("governance_state"))


if __name__ == "__main__":
    unittest.main()
