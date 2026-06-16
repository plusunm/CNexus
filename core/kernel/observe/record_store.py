"""Append-only kernel execution records — survives API restart."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class KernelRecordStore:
    def __init__(self, base_dir: str | Path) -> None:
        root = Path(base_dir)
        self._dir = root / "observability"
        self._path = self._dir / "kernel_records.jsonl"

    @property
    def path(self) -> Path:
        return self._path

    def append(self, row: dict[str, Any]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _load_index(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return {}
        index: dict[str, dict[str, Any]] = {}
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tid = str(row.get("trace_id") or "").strip()
                if tid:
                    index[tid] = row
        return index

    def get(self, trace_id: str) -> dict[str, Any] | None:
        tid = str(trace_id or "").strip()
        if not tid:
            return None
        return self._load_index().get(tid)

    def list_trace_ids(self, *, limit: int = 40) -> list[str]:
        if limit <= 0:
            return []
        index = self._load_index()
        return list(index.keys())[-limit:]
