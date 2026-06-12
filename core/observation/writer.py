"""Append-only observation bus writer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.observation.schema import ObservationEvent

DEFAULT_STREAM = "cnexus_observation.jsonl"


class ObservationWriter:
    """Append-only JSONL — never mutates history."""

    def __init__(self, base_dir: str | Path, *, stream_name: str = DEFAULT_STREAM) -> None:
        root = Path(base_dir)
        self._dir = root / "observability"
        self._path = self._dir / stream_name

    @property
    def path(self) -> Path:
        return self._path

    def append(self, record: dict[str, Any] | ObservationEvent) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        payload = record.to_dict() if isinstance(record, ObservationEvent) else record
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return self._path

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows
