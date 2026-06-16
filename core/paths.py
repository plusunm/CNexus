"""Resolve stable ASCII paths for runtime data (Windows / Unicode-safe)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


def get_project_root(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("BRAIN_MEMORY_ROOT")
    if env:
        return Path(env).resolve()
    return Path.cwd().resolve()


def _is_ascii_path(path: Path) -> bool:
    try:
        str(path).encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


def _program_data_root(project_root: Path) -> Path:
    """ASCII data root; isolate by project path hash when needed."""
    base = Path(os.environ.get("ProgramData", "C:/ProgramData")) / "cnexus" / "data"
    if _is_ascii_path(project_root):
        return base
    suffix = hashlib.sha256(str(project_root.resolve()).encode("utf-8")).hexdigest()[:10]
    return base / suffix


def _program_data_root_from_path(source: Path) -> Path:
    """ASCII-safe data root keyed by the original path (e.g. Unicode LOCALAPPDATA)."""
    base = Path(os.environ.get("ProgramData", "C:/ProgramData")) / "cnexus" / "data"
    suffix = hashlib.sha256(str(source.resolve()).encode("utf-8")).hexdigest()[:10]
    return base / suffix


def resolve_memory_dir(project_root: Path, base_dir: str = "memory") -> str:
    """
    Resolve memory storage directory.

    Priority:
    1. BM_MEMORY_DIR env (explicit override for production)
    2. project_root/base_dir when path is ASCII-safe
    3. C:/ProgramData/cnexus/data[/hash] for Unicode project paths
    """
    override = os.environ.get("BM_MEMORY_DIR")
    if override:
        path = Path(override).resolve()
        if not _is_ascii_path(path):
            path = _program_data_root_from_path(path)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    candidate = (project_root / base_dir).resolve()
    if _is_ascii_path(candidate):
        candidate.mkdir(parents=True, exist_ok=True)
        return str(candidate)

    fallback = _program_data_root(project_root)
    fallback.mkdir(parents=True, exist_ok=True)
    return str(fallback.resolve())


def ensure_runtime_data_dirs(memory_dir: str | Path) -> Path:
    """Create blocks/lancedb parents; leave kuzu_db path for Kuzu to own."""
    root = Path(memory_dir).expanduser().resolve()
    (root / "blocks").mkdir(parents=True, exist_ok=True)
    (root / "lancedb").mkdir(parents=True, exist_ok=True)
    (root / "kuzu_db").parent.mkdir(parents=True, exist_ok=True)
    kuzu_path = root / "kuzu_db"
    if kuzu_path.is_dir() and not any(kuzu_path.iterdir()):
        try:
            kuzu_path.rmdir()
        except OSError:
            pass
    return root
