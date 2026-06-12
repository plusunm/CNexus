"""Atomic JSON file writes for production durability."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


def _atomic_replace(tmp_path: Path, path: Path, *, retries: int = 5) -> None:
    """Replace destination with temp file; Windows may deny in-place replace on open targets."""
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError as exc:
            last_error = exc
            if os.name == "nt" and path.exists():
                try:
                    path.unlink()
                    os.replace(tmp_path, path)
                    return
                except OSError:
                    pass
            time.sleep(0.05 * (attempt + 1))
    if last_error is not None:
        raise last_error
    os.replace(tmp_path, path)


def atomic_write_json(path: Path, data: Any, *, indent: int = 2) -> None:
    """Write JSON via temp file + replace + fsync."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=indent)
            fh.flush()
            os.fsync(fh.fileno())
        _atomic_replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        _atomic_replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
