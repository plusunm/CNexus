"""Observation P2 — adapters, streaming L2, density management."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.observation import (
    FileTailAdapter,
    JsonlPushAdapter,
    MetricsScrapeAdapter,
    ObservationDensityManager,
    ObservationGateway,
    ObservationStreamTailer,
    build_streaming_l2_report,
)
from core.observation.density import DensityPolicy


class TestObservationP2(unittest.TestCase):
    def test_file_tail_ingests_new_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            external = Path(tmp) / "external.log"
            external.write_text('{"event":"a"}\n', encoding="utf-8")
            adapter = FileTailAdapter(tmp)
            r1 = adapter.poll(external)
            self.assertEqual(r1["ingested"], 1)
            external.write_text('{"event":"a"}\n{"event":"b"}\n', encoding="utf-8")
            r2 = adapter.poll(external)
            self.assertEqual(r2["ingested"], 1)

    def test_jsonl_push_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "batch.jsonl"
            f.write_text('{"k":1}\n{"k":2}\n', encoding="utf-8")
            result = JsonlPushAdapter(tmp).push_file(f)
            self.assertEqual(result["ingested"], 2)
            rows = ObservationGateway(tmp, enable_density=False)._writer.read_all()
            self.assertEqual(len(rows), 2)

    def test_metrics_scrape_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            mf = Path(tmp) / "m.json"
            mf.write_text('{"cpu": 0.5, "mem": 0.7}', encoding="utf-8")
            result = MetricsScrapeAdapter(tmp).scrape_json_file(mf)
            self.assertEqual(result["ingested"], 1)

    def test_density_hourly_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            policy = DensityPolicy(max_events_per_hour=2, max_events_per_source_hour=2, enable_chunk_compression=False)
            dm = ObservationDensityManager(tmp, policy)
            ok1, _ = dm.should_accept(source="test")
            dm.record_accepted("test")
            ok2, _ = dm.should_accept(source="test")
            dm.record_accepted("test")
            ok3, reason = dm.should_accept(source="test")
            self.assertTrue(ok1 and ok2)
            self.assertFalse(ok3)
            self.assertEqual(reason, "global_hourly_cap")

    def test_streaming_l2_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            gw = ObservationGateway(tmp, enable_density=False)
            gw.ingest(source="cnexus.chat", event_type="chat_turn", payload={"memory_context_chars": 100})
            report = build_streaming_l2_report(tmp, window_minutes=60)
            payload = report.to_dict()
            self.assertEqual(payload["observation_event_count"], 1)
            self.assertTrue(payload["metadata"]["streaming_l2"])

    def test_stream_tailer_poll(self):
        with tempfile.TemporaryDirectory() as tmp:
            gw = ObservationGateway(tmp, enable_density=False)
            gw.ingest(source="a", event_type="ping", payload={"n": 1})
            tailer = ObservationStreamTailer(tmp)
            first = tailer.poll_once()
            self.assertEqual(len(first), 1)
            gw.ingest(source="a", event_type="ping", payload={"n": 2})
            second = tailer.poll_once()
            self.assertEqual(len(second), 1)

    def test_temporal_loader_includes_observation_stream(self):
        from core.governance.l2.temporal.temporal_loader import load_stream_rows

        with tempfile.TemporaryDirectory() as tmp:
            ObservationGateway(tmp, enable_density=False).ingest(
                source="x", event_type="t", payload={"v": 1}
            )
            streams = load_stream_rows(tmp)
            self.assertIn("cnexus_observation", streams)
            self.assertEqual(len(streams["cnexus_observation"]), 1)


if __name__ == "__main__":
    unittest.main()
