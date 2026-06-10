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
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    candidate = (project_root / base_dir).resolve()
    if _is_ascii_path(candidate):
        candidate.mkdir(parents=True, exist_ok=True)
        return str(candidate)

    fallback = _program_data_root(project_root)
    fallback.mkdir(parents=True, exist_ok=True)
    return str(fallback.resolve())
