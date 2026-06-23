"""Tests for snapshot + incremental state reconstruction."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.audit_log import AuditLog  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402
from core.log_replay import LogReplayEngine  # noqa: E402
from core.state_reconstructor import StateReconstructor  # noqa: E402
from kernel.block_store import BlockStore  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "audit.log")
        snap_dir = os.path.join(tmp, "snapshots")
        key_path = os.path.join(tmp, "id.key")
        im = IdentityManager(key_path)
        audit = AuditLog(log_path)
        replay = LogReplayEngine(audit)
        recon = StateReconstructor(audit, replay, snap_dir, snapshot_interval=2)

        for i in range(5):
            audit.log(
                im,
                {
                    "event": "memory.block",
                    "block_id": f"mem-{i}",
                    "label": "episode",
                    "importance": 0.5,
                    "content_preview": f"memory {i}",
                },
            )

        ms = BlockStore()
        engine_state = {"trace": [], "current_iteration": 0, "consolidation": {}, "model_registry": {}}
        full = recon.reconstruct(memory_store=ms, engine_state=engine_state, force=True, reset=True)
        assert full.get("ok"), full
        assert len(ms.blocks) == 5, len(ms.blocks)

        audit.log(
            im,
            {
                "event": "memory.block",
                "block_id": "mem-5",
                "label": "episode",
                "importance": 0.6,
                "content_preview": "memory 5",
            },
        )

        ms2 = BlockStore()
        engine_state2 = {"trace": [], "current_iteration": 0, "consolidation": {}, "model_registry": {}}
        inc = recon.reconstruct(memory_store=ms2, engine_state=engine_state2, force=False, reset=True)
        assert inc.get("ok"), inc
        assert inc.get("mode") in ("incremental", "snapshot_only", "full"), inc
        assert len(ms2.blocks) == 6, (len(ms2.blocks), inc)

        latest = recon.load_latest_snapshot()
        assert latest and latest.get("entry_index") == 6, latest

        print("mode:", inc.get("mode"))
        print("blocks:", len(ms2.blocks))
        print("\nSTATE RECONSTRUCTOR TEST PASSED")


if __name__ == "__main__":
    main()
