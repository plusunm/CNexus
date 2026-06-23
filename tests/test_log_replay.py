"""Tests for AuditLog cognitive replay."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.audit_log import AuditLog  # noqa: E402
from core.identity_manager import IdentityManager  # noqa: E402
from core.log_replay import LogReplayEngine  # noqa: E402
from kernel.block_store import BlockStore  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "audit.log")
        key_path = os.path.join(tmp, "id.key")
        im = IdentityManager(key_path)
        audit = AuditLog(log_path)

        audit.log(im, {"event": "memory.block", "block_id": "mem-1", "label": "episode", "importance": 0.8, "content_preview": "hello memory"})
        audit.log(im, {"event": "trace.cycle", "trace_id": "trace-1", "iteration": 1, "input_preview": "what is CNexus"})
        audit.log(im, {"event": "asset.upload", "asset_id": "a" * 64, "type": "code", "filename": "demo.py", "summary": "demo handler"})

        ms = BlockStore()
        engine_state = {"trace": [], "current_iteration": 0, "consolidation": {}, "model_registry": {}}
        replay = LogReplayEngine(audit)
        report = replay.replay(memory_store=ms, engine_state=engine_state, reset=True)

        assert report.get("ok"), report
        assert len(ms.blocks) == 2, len(ms.blocks)
        assert len(engine_state["trace"]) == 1
        assert engine_state["current_iteration"] == 1

        print("blocks:", len(ms.blocks), "trace:", len(engine_state["trace"]))
        print("\nLOG REPLAY TEST PASSED")


if __name__ == "__main__":
    main()
