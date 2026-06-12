#!/usr/bin/env python3
"""Idempotent migration: legacy episodic vector rows -> typed MemoryBlocks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brain_memory import create_runtime
from memory.block import EPISODIC_TYPE_TO_LABEL


def migrate(runtime, *, dry_run: bool = False) -> dict:
    storage = runtime.storage
    manager = runtime.memory_manager

    rows = storage.vector.scan_memories() if hasattr(storage.vector, "scan_memories") else []
    migrated = 0
    skipped = 0
    by_type = {"event": 0, "dialogue": 0, "decision": 0}

    for row in rows:
        layer = str(row.get("layer", "episodic"))
        if layer not in {"episodic", "dialogue", "dialogue_trace", "event", "event_graph", "decision", "decision_trace"}:
            skipped += 1
            continue

        episodic_type = manager._infer_episodic_type(layer, str(row.get("role", "user")))
        episodic_id = str(row.get("memory_id") or row.get("id") or "")
        entry = {
            "role": row.get("role", "user"),
            "content": row.get("content", ""),
            "layer": layer,
            "importance": float(row.get("importance", 0.5)),
            "episodic_id": episodic_id,
            "migrated": True,
        }
        if dry_run:
            migrated += 1
            by_type[episodic_type] = by_type.get(episodic_type, 0) + 1
            continue

        manager.append_episodic_entry(episodic_type, entry, episodic_id=episodic_id or None)
        migrated += 1
        by_type[episodic_type] = by_type.get(episodic_type, 0) + 1

    report = {
        "dry_run": dry_run,
        "scanned": len(rows),
        "migrated": migrated,
        "skipped": skipped,
        "by_type": by_type,
        "labels": list(EPISODIC_TYPE_TO_LABEL.values()),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy episodic rows into typed blocks")
    parser.add_argument("--base-dir", default="memory")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()

    runtime = create_runtime(project_root=args.project_root, base_dir=args.base_dir)
    report = migrate(runtime, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
