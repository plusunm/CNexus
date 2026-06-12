#!/usr/bin/env python3
"""
CNexus Episodic Blocks Migration Script v0.1

Idempotent migration: legacy episodic vector rows -> typed MemoryBlocks.
Supports dry-run (default) and --group-triples for event→dialogue→decision ordering.

Stability-First: non-destructive preview by default; use --no-dry-run to apply.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brain_memory import create_runtime
from memory.block import EPISODIC_TYPE_TO_LABEL, BlockType


def _row_user_id(row: dict) -> str:
    meta = row.get("metadata") or {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return str(row.get("user_id") or meta.get("user_id") or "")


def _build_triple_payload(row: dict, episodic_type: str, episodic_id: str) -> dict:
    content = row.get("content", "")
    if episodic_type == "event":
        return {
            "event_id": episodic_id,
            "type": row.get("layer", "event"),
            "payload": content,
            "timestamp": row.get("timestamp"),
        }
    if episodic_type == "dialogue":
        return {
            "turn_id": episodic_id,
            "speaker": row.get("role", "user"),
            "content_summary": str(content)[:500],
        }
    return {
        "decision_id": episodic_id,
        "context_snapshot": row.get("context_snapshot") or content[:200],
        "chosen_action": content[:200],
        "outcome": row.get("outcome") or "",
        "reflection_id": row.get("reflection_id"),
    }


def migrate(
    runtime,
    *,
    dry_run: bool = True,
    group_triples: bool = False,
    user_id: Optional[str] = None,
) -> dict:
    storage = runtime.storage
    manager = runtime.memory_manager

    rows = storage.vector.scan_memories() if hasattr(storage.vector, "scan_memories") else []
    migrated = 0
    skipped = 0
    triples = 0
    user_filtered = 0
    by_type = {"event": 0, "dialogue": 0, "decision": 0}

    pending_event = None
    pending_dialogue = None

    for row in rows:
        if user_id:
            row_user = _row_user_id(row)
            if row_user and row_user != user_id:
                user_filtered += 1
                continue

        layer = str(row.get("layer", "episodic"))
        if layer not in {
            "episodic",
            "dialogue",
            "dialogue_trace",
            "event",
            "event_graph",
            "decision",
            "decision_trace",
        }:
            skipped += 1
            continue

        episodic_type = manager._infer_episodic_type(layer, str(row.get("role", "user")))
        episodic_id = str(row.get("memory_id") or row.get("id") or "")
        row_user = _row_user_id(row) or (user_id or "")
        row_session = str(row.get("session_id") or "")
        entry = {
            "role": row.get("role", "user"),
            "content": row.get("content", ""),
            "layer": layer,
            "importance": float(row.get("importance", 0.5)),
            "episodic_id": episodic_id,
            "migrated": True,
        }
        if row_user:
            entry["user_id"] = row_user
        if row_session:
            entry["session_id"] = row_session

        if group_triples:
            payload = _build_triple_payload(row, episodic_type, episodic_id)
            if episodic_type == "event":
                pending_event = payload
            elif episodic_type == "dialogue":
                pending_dialogue = payload
            else:
                if dry_run:
                    triples += 1 if pending_event and pending_dialogue else 0
                    migrated += 1
                    by_type["decision"] += 1
                elif pending_event and pending_dialogue:
                    manager.add_episodic_triple(
                        pending_event,
                        pending_dialogue,
                        payload,
                        user_id=row_user or None,
                        session_id=row_session or None,
                    )
                    triples += 1
                    migrated += 3
                    by_type["event"] += 1
                    by_type["dialogue"] += 1
                    by_type["decision"] += 1
                else:
                    if not dry_run:
                        manager.append_episodic_entry(
                            episodic_type, entry, episodic_id=episodic_id or None
                        )
                    migrated += 1
                    by_type[episodic_type] = by_type.get(episodic_type, 0) + 1
                pending_event = None
                pending_dialogue = None
            continue

        if dry_run:
            migrated += 1
            by_type[episodic_type] = by_type.get(episodic_type, 0) + 1
            continue

        manager.append_episodic_entry(episodic_type, entry, episodic_id=episodic_id or None)
        migrated += 1
        by_type[episodic_type] = by_type.get(episodic_type, 0) + 1

    report: Dict[str, Any] = {
        "dry_run": dry_run,
        "group_triples": group_triples,
        "user_id": user_id,
        "scanned": len(rows),
        "migrated": migrated,
        "triples": triples,
        "skipped": skipped,
        "user_filtered": user_filtered,
        "by_type": by_type,
        "labels": list(EPISODIC_TYPE_TO_LABEL.values()),
        "block_types": [member.value for member in BlockType if member.value.startswith("episodic")],
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migrate legacy episodic rows into typed MemoryBlocks (v0.1)",
    )
    parser.add_argument("--base-dir", default="memory")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--user-id", default=None, help="Migrate rows for a specific user only")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview only (default)",
    )
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="Execute live migration",
    )
    parser.add_argument(
        "--group-triples",
        action="store_true",
        help="When event→dialogue→decision rows appear in order, write via add_episodic_triple()",
    )
    args = parser.parse_args()

    print(
        f"[migrate] dry_run={args.dry_run}, group_triples={args.group_triples}"
        + (f", user_id={args.user_id}" if args.user_id else "")
    )

    runtime = create_runtime(project_root=args.project_root, base_dir=args.base_dir)
    report = migrate(
        runtime,
        dry_run=args.dry_run,
        group_triples=args.group_triples,
        user_id=args.user_id,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["dry_run"]:
        print("[migrate] DRY-RUN complete — use --no-dry-run to apply.")
    else:
        print("[migrate] LIVE migration applied. Check drift via GET /v1/status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
