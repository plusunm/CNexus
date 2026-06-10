"""P1.5 opt-in GTBS shadow hook tests."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain_memory import create_runtime


class TestGTBSShadowHook(unittest.TestCase):
    def test_shadow_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = create_runtime(base_dir=tmp)
            self.assertFalse(runtime._gtbs_shadow_enabled())
            out = runtime._gtbs_shadow_observe({"a": 1}, {"b": 2})
            self.assertIsNone(out)

    def test_shadow_enabled_returns_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = create_runtime(base_dir=tmp)
            runtime.config.setdefault("cdg", {})["enable_gtbs_shadow"] = True
            out = runtime._gtbs_shadow_observe(
                {"memory": [], "beliefs": []},
                {"memory": [{"id": "1"}], "beliefs": [], "flags": []},
                proposal={"target_stores": ["storage"]},
            )
            self.assertIsNotNone(out)
            self.assertEqual(out["type"], "gtbs_shadow_observation")
            self.assertTrue(out["non_actionable"])


if __name__ == "__main__":
    unittest.main()
