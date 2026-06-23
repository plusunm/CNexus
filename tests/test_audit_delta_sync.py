#!/usr/bin/env python3
"""AuditLog delta slice + gossip merge integration test."""

import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.audit_log import AuditLog  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402
from network.gossip_sync import GossipSync  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        key_path = os.path.join(tmp, "identity.key")
        log_peer = os.path.join(tmp, "peer_audit.log")
        log_local = os.path.join(tmp, "local_audit.log")
        im = IdentityManager(key_path)

        peer_audit = AuditLog(log_peer)
        for i in range(3):
            peer_audit.log(im, {"event": "peer.event", "seq": i})

        # Peer extends chain with two more entries
        peer_audit.log(im, {"event": "peer.event", "seq": 3})
        peer_audit.log(im, {"event": "peer.event", "seq": 4})

        # Local only has the first three (copy snapshot)
        shutil.copy(log_peer, log_local)
        with open(log_local, "r", encoding="utf-8") as handle:
            lines = [ln for ln in handle if ln.strip()]
        with open(log_local, "w", encoding="utf-8") as handle:
            handle.writelines(lines[:3])

        local_audit = AuditLog(log_local)
        assert local_audit.entry_count() == 3
        head_before = local_audit.last_hash

        entries, anchor_found = peer_audit.get_entries_since(head_before)
        print("delta_count:", len(entries), "anchor_found:", anchor_found)
        assert anchor_found
        assert len(entries) == 2

        ok, msg, count = local_audit.merge_entries(entries, im)
        print("merge:", ok, msg, count)
        assert ok and count == 2
        assert local_audit.last_hash == peer_audit.last_hash
        assert local_audit.verify_integrity(im)[0]

        # Fork panic: unknown anchor hash
        missing_entries, found = peer_audit.get_entries_since("deadbeef")
        assert not found
        assert missing_entries == []

        # GossipSync merge path (no HTTP — direct merge via shared objects)
        log_a = os.path.join(tmp, "a.log")
        log_b = os.path.join(tmp, "b.log")
        audit_a = AuditLog(log_a)
        audit_b = AuditLog(log_b)
        for i in range(2):
            audit_b.log(im, {"event": "sync", "n": i})
        shutil.copy(log_b, log_a)
        audit_a = AuditLog(log_a)
        audit_b.log(im, {"event": "sync", "n": 2})
        delta, anchor = audit_b.get_entries_since(audit_a.last_hash)
        assert anchor and len(delta) == 1
        gossip = GossipSync(audit_a, im, None)
        ok, msg, merged = audit_a.merge_entries(delta, im)
        assert ok and merged == 1
        assert gossip.local_head() == audit_b.last_hash

        print("\nAUDIT DELTA SYNC TEST PASSED")


if __name__ == "__main__":
    main()
