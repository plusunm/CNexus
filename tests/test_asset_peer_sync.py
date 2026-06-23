"""Tests for asset peer sync receive path."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.asset_processor import AssetProcessor  # noqa: E402
from network.asset_peer_sync import AssetPeerSync  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        asset_dir = os.path.join(tmp, "assets")
        proc = AssetProcessor(asset_dir)
        sync = AssetPeerSync(proc, peer_registry=None, max_push_bytes=1_000_000)

        content = b"print('peer pushed code')"
        asset_id = proc.content_hash(content)
        payload = {
            "action": "ASSET_PUSH",
            "asset_id": asset_id,
            "type": "code",
            "filename": "remote.py",
            "summary": "remote snippet",
            "size_bytes": len(content),
            "content_base64": __import__("base64").b64encode(content).decode("ascii"),
        }

        result = sync.receive(payload, peer_pubkey="peer-pubkey-test")
        assert result["ok"], result
        assert result["status"] == "received"

        again = sync.receive(payload, peer_pubkey="peer-pubkey-test")
        assert again.get("deduped") is True

        blob, meta, status = proc.read_raw(asset_id)
        assert status == 200 and blob == content

        print("asset_id:", asset_id[:16])
        print("\nASSET PEER SYNC TEST PASSED")


if __name__ == "__main__":
    main()
