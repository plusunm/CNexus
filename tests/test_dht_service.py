"""Tests for Kademlia DHT service."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.peer_registry import PeerRegistry  # noqa: E402
from network.dht_service import DHTService, peer_id, xor_distance  # noqa: E402


def main():
    a = "aa" * 32
    b = "bb" * 32
    id_a = peer_id(a)
    id_b = peer_id(b)
    assert xor_distance(id_a, id_b) > 0

    with tempfile.TemporaryDirectory() as tmp:
        reg = PeerRegistry(os.path.join(tmp, "peers.json"))
        reg.save_peer(a, "http://127.0.0.1:7864", status="trusted")

        dht = DHTService(a, peer_registry=reg, enabled=True)
        dht.seed_from_registry()
        dht.announce("http://127.0.0.1:7864", endpoints=["http://127.0.0.1:7864"])
        dht._touch_node(b, "http://127.0.0.1:7865")

        found = dht.find_node(b)
        assert found and found.get("pubkey") == b, found

        rpc = dht.handle_rpc({"action": "FIND_NODE", "target_id": peer_id(b)})
        assert rpc.get("ok") and rpc.get("nodes"), rpc

        status = dht.status()
        assert status["node_count"] >= 1, status

        print("dht_nodes:", status["node_count"])
        print("\nDHT SERVICE TEST PASSED")


if __name__ == "__main__":
    main()
