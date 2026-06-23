#!/usr/bin/env python3
"""Tamper-evidence test: 3 audit entries, mutate log, expect verify failure."""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from core.audit_log import AuditLog  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        key_path = os.path.join(tmp, "identity.key")
        log_path = os.path.join(tmp, "audit.log")
        im = IdentityManager(key_path)
        audit = AuditLog(log_path)

        thoughts = [
            {"event": "Reflect", "content": "CNexus 意识到自己是去中心化的"},
            {"event": "Store", "content": "第一条思维碎片"},
            {"event": "Decide", "content": "启动防篡改链验证"},
        ]
        for row in thoughts:
            audit.log(im, row)

        ok, msg = audit.verify_integrity(im)
        print("before_tamper:", ok, msg)
        if not ok:
            raise SystemExit("expected valid chain before tamper")

        raw = open(log_path, "r", encoding="utf-8").read()
        if len(raw) < 10:
            raise SystemExit("audit log too short")
        tampered = raw[:-2] + ("X" if raw[-2] != "X" else "Y") + raw[-1:]
        with open(log_path, "w", encoding="utf-8") as handle:
            handle.write(tampered)

        bad, bad_msg = audit.verify_integrity(im)
        print("after_tamper:", bad, bad_msg)
        if not bad:
            print("\nAUDIT TAMPER TEST PASSED")
            return
        raise SystemExit("expected integrity failure after tamper")


if __name__ == "__main__":
    main()
