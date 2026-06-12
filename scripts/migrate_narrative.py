#!/usr/bin/env python3
"""Migrate narrative summaries into narrative MemoryBlock."""

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
    summary = runtime.narrative.get_current_narrative_summary()
    coherence = runtime.narrative.narrative.narrative_coherence_score
    payload = {
        "summary": summary or "",
        "coherence": coherence,
        "source": "migrate_narrative",
    }
    if dry_run:
        existing = runtime.memory_manager.get_active_block("narrative", touch=False)
        return {
            "dry_run": True,
            "summary_len": len(summary or ""),
            "existing_block": existing.block_id if existing else None,
            "preview": payload,
        }
    with runtime_write_context():
        runtime.belief_engine._persist_narrative_block()
    block = runtime.memory_manager.get_active_block("narrative", touch=False)
    return {
        "dry_run": False,
        "block_id": block.block_id if block else None,
        "content_preview": (block.content[:200] if block else ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate narrative to narrative block")
    parser.add_argument("--base-dir", default="memory")
    parser.add_argument("--no-dry-run", action="store_true")
    args = parser.parse_args()
    result = migrate(base_dir=args.base_dir, dry_run=not args.no_dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
