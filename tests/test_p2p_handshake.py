#!/usr/bin/env python3
"""Simulate full P2P handshake between two identity managers."""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from api.p2p_handler import HandshakeHandler  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402
from core.peer_registry import PeerRegistry  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        im_a = IdentityManager(os.path.join(tmp, "a.key"))
        im_b = IdentityManager(os.path.join(tmp, "b.key"))
        node_a = HandshakeHandler(im_a)
        node_b = HandshakeHandler(im_b)
        registry = PeerRegistry(os.path.join(tmp, "peers.json"))

        pub_a = im_a.public_key_hex()
        pub_b = im_b.public_key_hex()

        # Step 1-2: A says hello to B, B challenges
        hello = node_b.handle_request({"action": "HELLO", "peer_pubkey": pub_a, "host": "http://127.0.0.1:7864"})
        assert hello["ok"], hello
        nonce = hello["nonce"]

        # Step 3: A signs response
        response = node_a.build_response(nonce, pub_b)

        # Step 4: B verifies and trusts A
        done = node_b.handle_request({
            "action": "HANDSHAKE_RESPONSE",
            "peer_pubkey": pub_a,
            "host": "http://127.0.0.1:7864",
            **response,
        })
        print("handshake:", done)
        assert done.get("status") == "trusted_peer"

        registry.save_peer(pub_a, "http://127.0.0.1:7864")
        assert pub_a in registry.get_all_peers()
        print("peers:", registry.get_all_peers())
        print("\nP2P HANDSHAKE TEST PASSED")


if __name__ == "__main__":
    main()
