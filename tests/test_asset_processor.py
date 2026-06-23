"""Tests for cognitive asset ingestion."""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.asset_processor import AssetProcessor, summarize_code_heuristic  # noqa: E402
from core.audit_log import AuditLog  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402


def _audit_factory(audit_log, identity_manager):
    def _fn(event, data):
        payload = {"event": event, **data}
        return audit_log.log(identity_manager, payload)

    return _fn


def main():
    with tempfile.TemporaryDirectory() as tmp:
        asset_dir = os.path.join(tmp, "assets")
        log_path = os.path.join(tmp, "audit.log")
        key_path = os.path.join(tmp, "identity.key")

        im = IdentityManager(key_path)
        audit = AuditLog(log_path)
        proc = AssetProcessor(
            asset_dir,
            audit_log=audit,
            audit_fn=_audit_factory(audit, im),
        )

        code = "class Demo:\n    def run(self):\n        return 42\n"
        code_result = proc.process_code(code, "demo.py")
        assert code_result["ok"], code_result
        assert code_result["type"] == "code"
        assert len(code_result["id"]) == 64

        dedup = proc.process_code(code, "demo.py")
        assert dedup.get("deduped") is True

        image = b"\x89PNG\r\n\x1a\nfake-image-bytes"
        image_result = proc.process_image(image, "diagram.png")
        assert image_result["ok"], image_result
        assert image_result["type"] == "image"

        meta, status = proc.get_asset(code_result["id"])
        assert status == 200
        assert meta["filename"] == "demo.py"

        content_payload, content_status = proc.get_asset(code_result["id"], include_content=True)
        assert content_status == 200
        assert "class Demo" in content_payload["content"]

        hits = proc.search("Demo", kind="code")
        assert hits, hits
        assert hits[0]["asset_id"] == code_result["id"]

        summary = summarize_code_heuristic(code, "demo.py")
        assert "class Demo" in summary

        print("code_id:", code_result["id"][:16])
        print("search_hits:", len(hits))
        print("\nASSET PROCESSOR TEST PASSED")


if __name__ == "__main__":
    main()
