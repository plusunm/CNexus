#!/usr/bin/env python3
"""Backup CNexus memory directory with manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.paths import get_project_root, resolve_memory_dir


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collect_manifest(source: Path) -> dict:
    files = []
    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue
        rel = item.relative_to(source).as_posix()
        files.append({"path": rel, "sha256": _sha256_file(item), "bytes": item.stat().st_size})
    return {
        "schema_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source.resolve()),
        "file_count": len(files),
        "files": files,
    }


def backup(*, project_root: Path, dest: Path, memory_dir: str | None = None) -> dict:
    source = Path(memory_dir or resolve_memory_dir(project_root, "memory")).resolve()
    if not source.exists():
        raise FileNotFoundError(f"memory dir not found: {source}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = dest / f"cnexus-memory-{stamp}"
    if target.exists():
        raise FileExistsError(f"backup target already exists: {target}")

    shutil.copytree(source, target)
    manifest = _collect_manifest(target)
    manifest_path = target / "backup_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    return {"backup_dir": str(target), "manifest": str(manifest_path), **manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup CNexus memory directory")
    parser.add_argument("--dest", type=Path, default=ROOT / "backups")
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--memory-dir", type=str, default=None)
    args = parser.parse_args()

    args.dest.mkdir(parents=True, exist_ok=True)
    report = backup(
        project_root=get_project_root(str(args.project_root)),
        dest=args.dest.resolve(),
        memory_dir=args.memory_dir,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
