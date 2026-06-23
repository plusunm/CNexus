#!/usr/bin/env python3
"""Smoke test: generate identity.key, sign a trace, verify signature."""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.identity_manager import IdentityManager  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        key_path = os.path.join(tmp, "identity.key")
        im = IdentityManager(key_path)

        trace = {
            "trace_id": "v2-trace-test-1",
            "iteration": 1,
            "input": "数字身份测试",
            "timestamp": 1719000000.0,
        }
        signed = im.sign_payload(trace)
        ok = im.verify_payload(signed, signed["pubkey"])

        init = im.handshake_init()
        challenge, nonce = im.handshake_challenge()
        response = im.handshake_response(nonce)
        handshake_ok = im.verify_handshake_response(response, nonce)

        print("pubkey:", im.public_key_hex())
        print("trace_sign_ok:", ok)
        print("handshake_ok:", handshake_ok)
        print("signed_envelope:", json.dumps(signed, ensure_ascii=False, indent=2))
        print("handshake_init:", json.dumps(init, ensure_ascii=False))

        if not (ok and handshake_ok):
            raise SystemExit(1)
        print("\nIDENTITY TEST PASSED")


if __name__ == "__main__":
    main()
