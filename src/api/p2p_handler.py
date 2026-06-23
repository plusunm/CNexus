"""P2P handshake — challenge/response trust establishment."""

from __future__ import annotations

import secrets
import time
from typing import Any, Dict, Optional


class HandshakeHandler:
    """Four-step trust handshake between CNexus nodes."""

    CHALLENGE_TTL_SECONDS = 120

    def __init__(self, identity_manager):
        self.id_mgr = identity_manager
        self.pending_challenges: Dict[str, Dict[str, Any]] = {}

    def _purge_expired(self):
        now = time.time()
        expired = [k for k, v in self.pending_challenges.items() if float(v.get("expires", 0)) < now]
        for key in expired:
            self.pending_challenges.pop(key, None)

    def local_pubkey(self) -> str:
        return self.id_mgr.public_key_hex()

    def initiate_hello(self) -> dict:
        """Node A announces identity (outbound preamble)."""
        return {
            "action": "HELLO",
            "pubkey": self.local_pubkey(),
        }

    def handle_hello(self, peer_pubkey: str, peer_host: Optional[str] = None) -> dict:
        """Step 1→2: peer says hello, we issue nonce challenge."""
        self._purge_expired()
        if not peer_pubkey:
            raise ValueError("peer_pubkey required")
        nonce = secrets.token_hex(16)
        self.pending_challenges[peer_pubkey] = {
            "nonce": nonce,
            "expires": time.time() + self.CHALLENGE_TTL_SECONDS,
            "host": peer_host or "",
        }
        return {
            "action": "HANDSHAKE_CHALLENGE",
            "nonce": nonce,
            "pubkey": self.local_pubkey(),
        }

    def build_response(self, nonce: str, peer_pubkey: str) -> dict:
        """Step 3: sign challenge nonce for peer."""
        signed = self.id_mgr.sign_payload({
            "nonce": nonce,
            "pubkey": self.local_pubkey(),
            "peer_pubkey": peer_pubkey,
        })
        return {"action": "HANDSHAKE_RESPONSE", **signed}

    def verify_response(self, peer_pubkey: str, response: dict) -> bool:
        """Step 4: verify peer signature against pending nonce."""
        self._purge_expired()
        pending = self.pending_challenges.get(peer_pubkey)
        if not pending:
            return False
        nonce = pending.get("nonce")
        if not nonce:
            return False
        if not self.id_mgr.verify_handshake_response(response, nonce):
            return False
        self.pending_challenges.pop(peer_pubkey, None)
        return True

    def pending_host(self, peer_pubkey: str) -> str:
        pending = self.pending_challenges.get(peer_pubkey) or {}
        return str(pending.get("host") or "")

    def handle_request(self, data: dict) -> dict:
        """Single entrypoint for POST /api/p2p/handshake."""
        action = str(data.get("action") or "HELLO").upper()
        peer_pubkey = str(data.get("peer_pubkey") or data.get("pubkey") or "").strip()
        peer_host = str(data.get("host") or data.get("peer_host") or "").strip()

        if action in ("HELLO", "HANDSHAKE_HELLO", "CHALLENGE_REQUEST", "HANDSHAKE_INIT"):
            if not peer_pubkey:
                return {"ok": False, "error": "missing_peer_pubkey"}
            challenge = self.handle_hello(peer_pubkey, peer_host)
            return {"ok": True, **challenge}

        if action == "HANDSHAKE_RESPONSE":
            if not peer_pubkey:
                peer_pubkey = str((data.get("payload") or {}).get("pubkey") or "")
            if not peer_pubkey:
                return {"ok": False, "error": "missing_peer_pubkey"}
            if not self.verify_response(peer_pubkey, data):
                return {"ok": False, "error": "handshake_failed"}
            return {
                "ok": True,
                "status": "trusted_peer",
                "pubkey": peer_pubkey,
                "host": peer_host or self.pending_host(peer_pubkey),
            }

        return {"ok": False, "error": "unknown_handshake_action", "action": action}
