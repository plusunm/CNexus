#!/usr/bin/env python3
"""Migrate in-memory BeliefEngine state into belief_store MemoryBlock."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain_memory.runtime import BrainMemoryRuntime
from memory.runtime_guard import runtime_write_context


def migrate(*, base_dir: str, dry_run: bool = True) -> dict:
    runtime = BrainMemoryRuntime(base_dir=base_dir, project_root=str(ROOT))
    payload = runtime.belief_engine.export_belief_store_payload()
    count = payload.get("count", 0)
    if dry_run:
        return {"dry_run": True, "beliefs": count, "preview": payload}
    with runtime_write_context():
        runtime.belief_engine._persist_belief_block()
    block = runtime.memory_manager.get_active_block("belief_store", touch=False)
    return {
        "dry_run": False,
        "beliefs": count,
        "block_id": block.block_id if block else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate beliefs to belief_store block")
    parser.add_argument("--base-dir", default="memory", help="Memory base directory")
    parser.add_argument("--no-dry-run", action="store_true", help="Persist belief_store block")
    args = parser.parse_args()
    result = migrate(base_dir=args.base_dir, dry_run=not args.no_dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
