"""Tests for genesis full-replication handshake."""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.audit_log import AuditLog  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402
from network.genesis_sync import GenesisSync, compute_resilience_score  # noqa: E402
from network.gossip_sync import GossipSync  # noqa: E402


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def main():
    with tempfile.TemporaryDirectory() as tmp:
        log_a = os.path.join(tmp, "a.log")
        log_b = os.path.join(tmp, "b.log")
        key = os.path.join(tmp, "id.key")

        im = IdentityManager(key)
        audit_a = AuditLog(log_a)
        audit_b = AuditLog(log_b)

        for i in range(5):
            audit_a.log(im, {"event": "test.genesis", "n": i})

        remote_entries = []
        for entry in audit_a.iter_entries():
            remote_entries.append(entry)

        def fake_urlopen(req, timeout=10):
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if url.endswith("/api/peer/sync"):
                body = json.loads(req.data.decode("utf-8"))
                return _FakeResponse({
                    "ok": True,
                    "last_hash": audit_a.last_hash,
                    "audit_entries": audit_a.entry_count(),
                    "integrity_ok": True,
                })
            if "/api/peer/audit" in url:
                return _FakeResponse({
                    "ok": True,
                    "anchor_found": True,
                    "entries": remote_entries,
                    "last_hash": audit_a.last_hash,
                    "has_more": False,
                })
            raise RuntimeError(f"unexpected url {url}")

        import urllib.request as urlrequest

        urlrequest.urlopen = fake_urlopen

        gossip_b = GossipSync(audit_b, im, None)
        genesis = GenesisSync(gossip_b, enabled=True, jitter_min=0, jitter_max=0, chunk_size=200)
        gossip_b.attach_genesis(genesis)

        result = genesis.genesis_handshake("http://127.0.0.1:9001", peer_pubkey="peer-test")
        assert result.get("ok"), result
        assert audit_b.last_hash == audit_a.last_hash
        assert audit_b.entry_count() == audit_a.entry_count()

        score = compute_resilience_score(
            peer_rows=[{"status": "online", "aligned": True}],
            local_integrity_ok=True,
        )
        assert score["score"] >= 0.5, score

        print("merged:", result.get("status"))
        print("resilience:", score["score"])
        print("\nGENESIS SYNC TEST PASSED")


if __name__ == "__main__":
    main()
