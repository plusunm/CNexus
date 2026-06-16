"""Append-only execution_tap.jsonl — cross-process tap replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ExecutionTapLog:
    def __init__(self, base_dir: str | Path) -> None:
        root = Path(base_dir)
        self._dir = root / "observability"
        self._path = self._dir / "execution_tap.jsonl"

    @property
    def path(self) -> Path:
        return self._path

    def append(self, row: dict[str, Any]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with open(self._path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def events_for_trace(self, trace_id: str) -> list[dict[str, Any]]:
        return [r for r in self.read_all() if str(r.get("trace_id") or "") == trace_id]
