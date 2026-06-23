#!/usr/bin/env python3
"""Auth middleware tests: valid, expired, forged signatures."""

import os
import sys
import time
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from api.middleware import (  # noqa: E402
    build_signed_headers,
    verify_cnexus_auth,
)
from core.identity_manager import IdentityManager  # noqa: E402


class _Headers(dict):
    def get(self, key, default=None):
        return super().get(key, super().get(key.lower(), default))


def main():
    with tempfile.TemporaryDirectory() as tmp:
        im_a = IdentityManager(os.path.join(tmp, "a.key"))
        im_b = IdentityManager(os.path.join(tmp, "b.key"))
        payload = {"action": "peer.sync", "cursor": 0}

        # Case A — valid
        headers = build_signed_headers(im_a, payload)
        ok, err, status = verify_cnexus_auth(_Headers(headers), payload, im_a)
        print("case_a:", ok, status, err)
        if not ok:
            raise SystemExit(1)

        # Case B — expired (60s old)
        old_ts = time.time() - 60
        stale = build_signed_headers(im_a, payload, timestamp=old_ts)
        ok, err, status = verify_cnexus_auth(_Headers(stale), payload, im_a, max_skew=30)
        print("case_b:", ok, status, err.get("error"))
        if ok or status != 403:
            raise SystemExit("expected 403 expired")

        # Case C — forged (B signs but claims A's pubkey)
        forged = build_signed_headers(im_b, payload)
        forged["X-CNexus-Pubkey"] = im_a.public_key_hex()
        ok, err, status = verify_cnexus_auth(_Headers(forged), payload, im_a)
        print("case_c:", ok, status, err.get("error"))
        if ok or status != 403:
            raise SystemExit("expected 403 forbidden")

        print("\nAUTH MIDDLEWARE TEST PASSED")


if __name__ == "__main__":
    main()
