"""File tail adapter — external logs → Observation Bus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.observation.gateway import ObservationGateway


class FileTailAdapter:
    """Tail an external file (log/jsonl) and ingest new lines via Gateway."""

    def __init__(self, base_dir: str | Path, *, source_label: str = "external.file_tail") -> None:
        self.gateway = ObservationGateway(base_dir)
        self.source_label = source_label
        self._offset_path = Path(base_dir) / "observability" / ".file_tail_offsets.json"
        self._offsets = self._load_offsets()

    def _load_offsets(self) -> dict[str, int]:
        if not self._offset_path.exists():
            return {}
        try:
            return dict(json.loads(self._offset_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_offsets(self) -> None:
        self._offset_path.parent.mkdir(parents=True, exist_ok=True)
        self._offset_path.write_text(json.dumps(self._offsets, indent=2), encoding="utf-8")

    def _parse_line(self, line: str) -> dict[str, Any]:
        line = line.strip()
        if not line:
            return {}
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        return {"raw_line": line[:2000]}

    def poll(self, file_path: str | Path, *, event_type: str = "log_line") -> dict[str, Any]:
        path = Path(file_path).resolve()
        key = str(path)
        start = self._offsets.get(key, 0)
        if not path.exists():
            return {"ingested": 0, "error": "file_not_found", "path": key}

        ingested = 0
        skipped = 0
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(start)
            for line in fh:
                payload = self._parse_line(line)
                if not payload:
                    continue
                result = self.gateway.ingest_with_density(
                    source=self.source_label,
                    event_type=event_type,
                    payload={**payload, "tail_path": path.name},
                )
                if result.get("meta", {}).get("accepted") is False:
                    skipped += 1
                else:
                    ingested += len(result.get("records") or [])
            self._offsets[key] = fh.tell()
        self._save_offsets()
        return {"ingested": ingested, "skipped": skipped, "path": key, "offset": self._offsets[key]}
