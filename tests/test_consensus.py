#!/usr/bin/env python3
"""Consensus negotiation unit tests."""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.audit_log import AuditLog  # noqa: E402
from core.consensus import NegotiationManager  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402
from core.reputation_registry import ReputationRegistry  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        im = IdentityManager(os.path.join(tmp, "id.key"))
        log_a = os.path.join(tmp, "a.log")
        log_b = os.path.join(tmp, "b.log")
        audit_a = AuditLog(log_a)
        audit_b = AuditLog(log_b)

        for i in range(3):
            audit_a.log(im, {"event": "shared", "n": i})

        import shutil
        shutil.copy(log_a, log_b)
        audit_b = AuditLog(log_b)
        audit_b.log(im, {"event": "shared", "n": 3})
        audit_b.log(im, {"event": "shared", "n": 4})

        ancestor = audit_a.find_common_ancestor(audit_b.get_proof_hashes())
        print("ancestor:", ancestor[:16] if ancestor != "0" else "0")
        assert ancestor == audit_a.last_hash

        tail, found = audit_b.get_entries_since(ancestor)
        assert found and len(tail) == 2

        rep = ReputationRegistry(os.path.join(tmp, "rep.json"))
        pub = im.public_key_hex()
        neg = NegotiationManager(audit_a, im, rep, mode="optimistic")

        init = {"action": "NEGOTIATE_INIT", "local_head": audit_b.last_hash, "proof_hashes": audit_b.get_proof_hashes(), "pubkey": pub}
        vote = neg.handle_negotiate(init, pub)
        print("vote:", vote.get("vote"), vote.get("common_ancestor", "")[:8])
        assert vote.get("ok")

        ok, msg, count = audit_a.reorg_from_ancestor(ancestor, tail, im)
        print("reorg:", ok, msg, count)
        assert ok and count == 2
        assert audit_a.last_hash == audit_b.last_hash

        rep.record_fraud("bad-peer", reason="test")
        assert rep.get_trust("bad-peer") < 0.5

        print("\nCONSENSUS TEST PASSED")


if __name__ == "__main__":
    main()
