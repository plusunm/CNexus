"""Tests for network-layer firewall."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.reputation_registry import ReputationRegistry  # noqa: E402
from network.network_firewall import NetworkFirewall  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        rep = ReputationRegistry(os.path.join(tmp, "rep.json"))
        fw = NetworkFirewall(rep, min_trust_discovered=0.3)
        peer = "cc" * 32

        ok, _ = fw.allow_connection(peer, status="discovered")
        assert ok

        fw.ban_peer(peer, reason="tamper_test")
        assert fw.is_banned(peer)
        ok2, reason = fw.allow_connection(peer, status="trusted")
        assert not ok2 and reason == "peer_banned"

        peers = {peer: {"host": "http://x", "status": "trusted"}, "dd" * 32: {"host": "http://y", "status": "trusted"}}
        filtered = fw.filter_peers(peers)
        assert peer not in filtered
        assert "dd" * 32 in filtered

        print("\nNETWORK FIREWALL TEST PASSED")


if __name__ == "__main__":
    main()
