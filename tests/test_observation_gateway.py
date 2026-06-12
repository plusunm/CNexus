"""Observation Gateway v1 tests."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.observation import (
    EventNormalizer,
    ObservationGateway,
    demote_payload,
    record_chat_observation,
)
from core.observation.schema import CONTROL_STRIP_KEYS


class TestObservationGateway(unittest.TestCase):
    def test_strip_control_keys(self):
        normalizer = EventNormalizer()
        out = normalizer.strip_control_fields({"action": "x", "message": "hi", "winner": "a"})
        self.assertNotIn("action", out)
        self.assertNotIn("winner", out)
        self.assertIn("message", out)

    def test_demotion_winner_to_precedence_label(self):
        demoted = demote_payload({"winner": "runtime_safety", "nested": {"risk": "high"}})
        self.assertIn("precedence_label", demoted)
        self.assertNotIn("winner", demoted)

    def test_gateway_append_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            gw = ObservationGateway(tmp)
            gw.ingest(source="test", event_type="ping", payload={"value": 1})
            gw.ingest(source="test", event_type="ping", payload={"value": 2})
            rows = gw._writer.read_all()
            self.assertEqual(len(rows), 2)
            self.assertTrue(rows[0]["envelope"]["observational_only"])

    def test_record_chat_observation_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "cfg.json"
            cfg.write_text(
                json.dumps(
                    {
                        "embedding_fallback": "hash",
                        "runtime_mode": "g2",
                        "vector_dim": 768,
                        "cdg": {"enable_gtbs_shadow": False, "enable_gtbs_capture": False},
                    }
                ),
                encoding="utf-8",
            )
            from brain_memory.runtime import BrainMemoryRuntime

            runtime = BrainMemoryRuntime(config_path=str(cfg), base_dir=tmp, project_root=str(Path(__file__).resolve().parents[1]))
            meta = record_chat_observation(
                runtime,
                message="hello observation bus",
                use_memory=True,
                memory_context_chars=10,
                capture={"user": "ok-id"},
                model_name="test-model",
                pre_state={},
            )
            stream = Path(meta["observation_stream"])
            self.assertTrue(stream.exists())
            rows = stream.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreaterEqual(len(rows), 1)
            row = json.loads(rows[-1])
            self.assertEqual(row["source"], "cnexus.chat")
            self.assertTrue(row["payload"].get("observational_safe"))

    def test_control_strip_keys_frozen(self):
        self.assertIn("action", CONTROL_STRIP_KEYS)
        self.assertIn("commit", CONTROL_STRIP_KEYS)


if __name__ == "__main__":
    unittest.main()
