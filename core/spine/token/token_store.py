"""Token event persistence — append-only JSONL under observability/."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Optional

_STORE_NAME = "token_spine.jsonl"
_lock = threading.Lock()
_persist_base: Optional[Path] = None


def configure_token_store(base_dir: str | Path) -> None:
    global _persist_base
    root = Path(base_dir) / "observability"
    root.mkdir(parents=True, exist_ok=True)
    _persist_base = root


def _store_path(base_dir: str | Path | None = None) -> Path:
    if base_dir is not None:
        return Path(base_dir) / "observability" / _STORE_NAME
    if _persist_base is not None:
        return _persist_base / _STORE_NAME
    return Path("observability") / _STORE_NAME


def append_token_event(event: dict[str, Any], *, base_dir: str | Path | None = None) -> None:
    path = _store_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    row = dict(event)
    if "timestamp" not in row:
        row["timestamp"] = time.time()
    with _lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_all_tokens(*, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    path = _store_path(base_dir)
    if not path.exists():
        return []
    result: list[dict[str, Any]] = []
    with _lock:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return result


def read_tokens(trace_id: str, *, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
    return [e for e in read_all_tokens(base_dir=base_dir) if str(e.get("trace_id") or "") == trace_id]
