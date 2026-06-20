"""Layer 2 — daily-sharded trace store tests."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.runtime.execution_trace import append_execution_trace, trace_file_path, trace_stats
from core.runtime.trace_store import (
    list_trace_shards,
    migrate_legacy_trace_file,
    shard_path,
    trace_stats as store_trace_stats,
)


class TestTraceStoreSharding(unittest.TestCase):
    def test_append_writes_daily_shard(self) -> None:
        base = tempfile.mkdtemp()
        append_execution_trace(base, {"type": "l3_tick", "ticks": 1})
        shard = trace_file_path(base)
        self.assertIsNotNone(shard)
        assert shard is not None
        self.assertEqual(shard.parent.name, "traces")
        self.assertEqual(shard.name, f"{date.today().isoformat()}.jsonl")
        self.assertTrue(shard.exists())

    def test_trace_stats_tail_across_shards(self) -> None:
        base = tempfile.mkdtemp()
        root = Path(base)
        traces = root / "traces"
        traces.mkdir()
        day1 = traces / "2026-06-16.jsonl"
        day2 = traces / "2026-06-17.jsonl"
        rows1 = [
            {"ts": datetime(2026, 6, 16, 12, tzinfo=timezone.utc).timestamp(), "mono_ms": 1, "type": "l3_tick"},
            {"ts": datetime(2026, 6, 16, 12, 1, tzinfo=timezone.utc).timestamp(), "mono_ms": 2, "type": "l3_tick"},
        ]
        rows2 = [
            {"ts": datetime(2026, 6, 17, 8, tzinfo=timezone.utc).timestamp(), "mono_ms": 3, "type": "interaction_step"},
            {"ts": datetime(2026, 6, 17, 8, 1, tzinfo=timezone.utc).timestamp(), "mono_ms": 4, "type": "l3_tick"},
        ]
        day1.write_text("\n".join(json.dumps(r) for r in rows1) + "\n", encoding="utf-8")
        day2.write_text("\n".join(json.dumps(r) for r in rows2) + "\n", encoding="utf-8")

        stats = store_trace_stats(base, tail_lines=3)
        self.assertEqual(stats["total_lines"], 4)
        self.assertEqual(stats["shard_count"], 2)
        self.assertEqual(stats["l3_tick_count"], 2)
        self.assertEqual(stats["interaction_step_count"], 1)
        self.assertEqual(stats["last_event_type"], "l3_tick")

    def test_migrate_legacy_single_file(self) -> None:
        base = tempfile.mkdtemp()
        legacy = Path(base) / "execution_trace.jsonl"
        ts = datetime(2026, 6, 15, 10, tzinfo=timezone.utc).timestamp()
        legacy.write_text(
            json.dumps({"ts": ts, "mono_ms": 10, "type": "kernel_execution", "trace_id": "t-abc"}) + "\n",
            encoding="utf-8",
        )
        self.assertTrue(migrate_legacy_trace_file(base))
        self.assertFalse(legacy.exists())
        shards = list_trace_shards(base)
        self.assertEqual(len(shards), 1)
        self.assertEqual(shards[0].name, "2026-06-15.jsonl")
        row = json.loads(shards[0].read_text(encoding="utf-8").strip())
        self.assertEqual(row["type"], "kernel_execution")

    def test_concurrent_append_per_shard_lock(self) -> None:
        base = tempfile.mkdtemp()
        errors: list[str] = []

        def worker(n: int) -> None:
            try:
                for i in range(20):
                    append_execution_trace(base, {"type": "l3_tick", "worker": n, "i": i})
            except Exception as exc:  # pragma: no cover
                errors.append(str(exc))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        self.assertEqual(errors, [])
        stats = trace_stats(base)
        self.assertEqual(stats["total_lines"], 80)
        self.assertEqual(stats["l3_tick_count"], 80)

    def test_shard_path_resolution(self) -> None:
        base = tempfile.mkdtemp()
        path = shard_path(base, date(2026, 6, 18))
        self.assertIsNotNone(path)
        assert path is not None
        self.assertTrue(str(path).endswith("traces\\2026-06-18.jsonl") or str(path).endswith("traces/2026-06-18.jsonl"))


if __name__ == "__main__":
    unittest.main()
