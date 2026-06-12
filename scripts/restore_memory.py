#!/usr/bin/env python3
"""Restore CNexus memory directory from backup."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.paths import get_project_root, resolve_memory_dir


def _verify_manifest(backup_dir: Path) -> dict:
    manifest_path = backup_dir / "backup_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing manifest: {manifest_path}")
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    for entry in manifest.get("files", []):
        rel = entry.get("path")
        if not rel or rel == "backup_manifest.json":
            continue
        target = backup_dir / rel
        if not target.exists():
            raise FileNotFoundError(f"backup file missing: {rel}")
    return manifest


def restore(
    *,
    backup_dir: Path,
    project_root: Path,
    memory_dir: str | None = None,
    force: bool = False,
) -> dict:
    backup_dir = backup_dir.resolve()
    manifest = _verify_manifest(backup_dir)
    target = Path(memory_dir or resolve_memory_dir(project_root, "memory")).resolve()

    if target.exists() and not force:
        raise FileExistsError(
            f"target memory dir exists ({target}); pass --force to overwrite after safety copy"
        )

    safety_copy = None
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safety_copy = target.parent / f"{target.name}.pre-restore-{stamp}"
        shutil.move(str(target), str(safety_copy))

    target.mkdir(parents=True, exist_ok=True)
    for item in backup_dir.iterdir():
        if item.name == "backup_manifest.json":
            continue
        dest = target / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    return {
        "restored_to": str(target),
        "backup_dir": str(backup_dir),
        "manifest_file_count": manifest.get("file_count", 0),
        "safety_copy": str(safety_copy) if safety_copy else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore CNexus memory from backup")
    parser.add_argument("backup_dir", type=Path)
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--memory-dir", type=str, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    report = restore(
        backup_dir=args.backup_dir,
        project_root=get_project_root(str(args.project_root)),
        memory_dir=args.memory_dir,
        force=args.force,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
