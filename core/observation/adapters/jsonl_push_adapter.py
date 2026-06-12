"""JSONL push adapter — batch ingest external event files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.observation.gateway import ObservationGateway


class JsonlPushAdapter:
    """Push a JSONL file (or list of dicts) into Observation Bus."""

    def __init__(self, base_dir: str | Path, *, source_label: str = "external.jsonl_push") -> None:
        self.gateway = ObservationGateway(base_dir)
        self.source_label = source_label

    def push_file(self, file_path: str | Path, *, event_type: str = "pushed_event") -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"ingested": 0, "error": "file_not_found"}
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return self.push_lines(lines, event_type=event_type, source_override=f"{self.source_label}:{path.name}")

    def push_lines(
        self,
        lines: list[str],
        *,
        event_type: str = "pushed_event",
        source_override: str | None = None,
    ) -> dict[str, Any]:
        source = source_override or self.source_label
        ingested = 0
        skipped = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                payload = {"raw_line": line[:2000]}
            if not isinstance(payload, dict):
                payload = {"value": payload}
            result = self.gateway.ingest_with_density(
                source=source,
                event_type=str(payload.get("event_type", event_type)),
                payload=payload,
            )
            if result.get("meta", {}).get("accepted") is False:
                skipped += 1
            else:
                ingested += len(result.get("records") or [])
        return {"ingested": ingested, "skipped": skipped, "source": source}

    def push_events(self, events: list[dict[str, Any]], *, source: str | None = None) -> dict[str, Any]:
        lines = [json.dumps(e, ensure_ascii=False) for e in events]
        return self.push_lines(lines, source_override=source or self.source_label)
