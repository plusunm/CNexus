"""Tests for asset push retry queue."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.asset_processor import AssetProcessor  # noqa: E402
from network.asset_peer_sync import AssetPeerSync  # noqa: E402
from network.asset_push_queue import AssetPushRetryQueue  # noqa: E402


class _FailingSync:
    def __init__(self):
        self.calls = 0

    def push_to_peer(self, host, pubkey, asset_id):
        self.calls += 1
        if self.calls < 3:
            return {"ok": False, "error": "connection refused"}
        return {"ok": True, "asset_id": asset_id, "peer_host": host}


def main():
    with tempfile.TemporaryDirectory() as tmp:
        queue_path = os.path.join(tmp, "push_queue.json")
        sync = _FailingSync()
        queue = AssetPushRetryQueue(
            queue_path,
            sync,
            base_delay_s=0.01,
            max_delay_s=0.05,
            poll_interval_s=60,
            max_attempts=5,
        )

        row = queue.enqueue("a" * 64, "http://127.0.0.1:9999", error="connection refused")
        assert row["ok"] and row["queued"], row
        assert queue.pending_count() == 1

        item = queue.list_items(limit=1)[0]
        item["next_retry_at"] = 0
        queue._items[0] = item
        queue._persist()

        report = queue.process_pending(limit=5)
        assert report["processed"] >= 1, report
        assert sync.calls >= 1

        item = queue.list_items(limit=1)[0]
        item["next_retry_at"] = 0
        queue._items[0] = item
        queue._persist()
        report2 = queue.process_pending(limit=5)
        assert report2["processed"] >= 1, report2

        item = queue.list_items(limit=1)[0]
        item["next_retry_at"] = 0
        queue._items[0] = item
        queue._persist()
        report3 = queue.process_pending(limit=5)
        assert report3["succeeded"] >= 1 or any(
            row.get("status") == "done" for row in queue.list_items()
        ), report3

        dead = queue.enqueue("b" * 64, "http://peer", error="asset_too_large (9 > 1)")
        assert dead["ok"] is False

        asset_dir = os.path.join(tmp, "assets")
        proc = AssetProcessor(asset_dir)
        peer_sync = AssetPeerSync(proc, peer_registry=None)
        peer_sync.push_queue = queue
        code_result = proc.process_code("print('retry')", "retry.py")
        assert code_result["ok"]

        def _fail_post(self, host, path, payload):
            raise ConnectionError("connection refused")

        peer_sync._http_post = _fail_post.__get__(peer_sync, AssetPeerSync)
        result = peer_sync.push_to_peer("http://127.0.0.1:1", "pk", code_result["id"])
        assert result.get("retry_queued") is True

        print("pending:", queue.pending_count())
        print("\nASSET PUSH QUEUE TEST PASSED")


if __name__ == "__main__":
    main()
