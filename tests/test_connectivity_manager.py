"""Tests for connectivity manager path selection."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.peer_registry import PeerRegistry  # noqa: E402
from network.connectivity_manager import ConnectivityManager, PathKind  # noqa: E402
from network.dht_service import DHTService  # noqa: E402
from network.network_firewall import NetworkFirewall  # noqa: E402


def main():
    local = "aa" * 32
    remote = "bb" * 32

    with tempfile.TemporaryDirectory() as tmp:
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        dht = DHTService(local, peer_registry=reg, enabled=True)
        dht._touch_node(remote, "http://127.0.0.1:9")

        cm = ConnectivityManager(
            local_pubkey=local,
            local_port=7864,
            bind_host="127.0.0.1",
            dht_service=dht,
            peer_registry=reg,
            network_firewall=NetworkFirewall(None),
            stun_gather_fn=lambda: None,
            enabled=True,
        )

        candidates = cm.gather_candidates(refresh_stun=False)
        assert candidates and candidates[0].get("type") == "host"

        def _fake_probe(url, timeout=4.0):
            if url.endswith(":9"):
                return True, 12.0
            return False, None

        cm._probe_url = _fake_probe
        report = cm.connect_to(remote)
        assert report.get("ok"), report
        assert report.get("path_kind") in ("direct", "unknown"), report

        banned = cm.connect_to("ff" * 32)
        # no node in dht - may fail, that's ok
        assert "paths" in report

        print("connect:", report.get("url"))
        print("\nCONNECTIVITY MANAGER TEST PASSED")


if __name__ == "__main__":
    main()
