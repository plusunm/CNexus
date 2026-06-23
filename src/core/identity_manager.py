"""Ed25519 node identity — key lifecycle, payload signing, and handshake helpers."""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import nacl.encoding
import nacl.signing


class IdentityManager:
    """Local sovereign identity anchor (Ed25519 via PyNaCl)."""

    def __init__(self, storage_path: str | Path = "data/identity.key"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.signing_key = self._load_or_create_identity()
        self.verify_key = self.signing_key.verify_key

    def _load_or_create_identity(self) -> nacl.signing.SigningKey:
        if self.storage_path.exists():
            seed = self.storage_path.read_bytes()
            if len(seed) != nacl.signing.SigningKey.SEED_SIZE:
                raise ValueError(f"invalid identity seed size: {len(seed)}")
            return nacl.signing.SigningKey(seed)
        signing_key = nacl.signing.SigningKey.generate()
        self.storage_path.write_bytes(signing_key.encode())
        return signing_key

    def public_key_hex(self) -> str:
        return self.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode("utf-8")

    @staticmethod
    def _canonical_json(data: dict) -> bytes:
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def sign_payload(self, data: dict) -> dict:
        """Sign a payload; returns envelope with payload, signature, pubkey."""
        data_bytes = self._canonical_json(data)
        signed = self.signing_key.sign(data_bytes)
        return {
            "payload": data,
            "signature": signed.signature.hex(),
            "pubkey": self.public_key_hex(),
            "algorithm": "Ed25519",
        }

    def verify_payload(self, signed_data: dict, public_key_hex: Optional[str] = None) -> bool:
        try:
            pubkey = public_key_hex or signed_data.get("pubkey")
            if not pubkey:
                return False
            verify_key = nacl.signing.VerifyKey(pubkey.encode(), encoder=nacl.encoding.HexEncoder)
            payload = signed_data.get("payload")
            if not isinstance(payload, dict):
                return False
            data_bytes = self._canonical_json(payload)
            verify_key.verify(data_bytes, bytes.fromhex(signed_data["signature"]))
            return True
        except Exception:
            return False

    # ── Identity Handshake Protocol ─────────────────────────────────────

    def handshake_init(self) -> dict:
        return {"action": "HANDSHAKE_INIT", "pubkey": self.public_key_hex()}

    def handshake_challenge(self) -> Tuple[dict, str]:
        nonce = secrets.token_hex(16)
        return {"action": "HANDSHAKE_CHALLENGE", "nonce": nonce}, nonce

    def handshake_response(self, nonce: str) -> dict:
        signed = self.sign_payload({"nonce": nonce, "pubkey": self.public_key_hex()})
        return {"action": "HANDSHAKE_RESPONSE", **signed}

    def verify_handshake_response(self, response: dict, expected_nonce: str) -> bool:
        payload = response.get("payload") or {}
        if payload.get("nonce") != expected_nonce:
            return False
        pubkey = payload.get("pubkey") or response.get("pubkey")
        if not pubkey:
            return False
        return self.verify_payload(response, pubkey)
