"""Streaming tail — read new observation bus lines incrementally."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.observation.writer import DEFAULT_STREAM, ObservationWriter


@dataclass
class TailState:
    byte_offset: int = 0
    events_seen: int = 0
    last_timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "byte_offset": self.byte_offset,
            "events_seen": self.events_seen,
            "last_timestamp": self.last_timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TailState:
        return cls(
            byte_offset=int(data.get("byte_offset", 0)),
            events_seen=int(data.get("events_seen", 0)),
            last_timestamp=data.get("last_timestamp"),
        )


class ObservationStreamTailer:
    """Tail -f style reader for cnexus_observation.jsonl (read-only)."""

    def __init__(self, base_dir: str | Path, *, stream_name: str = DEFAULT_STREAM) -> None:
        self.base_dir = Path(base_dir)
        self.writer = ObservationWriter(base_dir, stream_name=stream_name)
        self._state_path = self.base_dir / "observability" / f".tail_state_{stream_name}.json"
        self.state = self._load_state()

    def _load_state(self) -> TailState:
        if not self._state_path.exists():
            return TailState()
        try:
            return TailState.from_dict(json.loads(self._state_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return TailState()

    def _save_state(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(self.state.to_dict(), indent=2), encoding="utf-8")

    def poll_once(self) -> list[dict[str, Any]]:
        path = self.writer.path
        if not path.exists():
            return []
        new_rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(self.state.byte_offset)
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    new_rows.append(row)
                    self.state.events_seen += 1
                    if row.get("timestamp"):
                        self.state.last_timestamp = row["timestamp"]
                except json.JSONDecodeError:
                    continue
            self.state.byte_offset = fh.tell()
        self._save_state()
        return new_rows

    def read_window_rows(self, *, max_rows: int = 500) -> list[dict[str, Any]]:
        """Read trailing rows for rolling L2 window (does not advance tail offset)."""
        path = self.writer.path
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        tail_lines = lines[-max_rows:] if len(lines) > max_rows else lines
        rows: list[dict[str, Any]] = []
        for line in tail_lines:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows
