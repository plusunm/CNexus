"""
GTBS v1.2 — parallel transaction event stream (not governance cycle audit).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.governance.gtbs.types import AuditTransactionEvent


class GTBSTransactionLog:
    """Append-only GTBS proposal / approval / commit events."""

    def __init__(self, base_dir: str | Path) -> None:
        root = Path(base_dir)
        self._dir = root / "observability"
        self._path = self._dir / "gtbs_transactions.jsonl"

    @property
    def path(self) -> Path:
        return self._path

    def append(self, event: AuditTransactionEvent) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

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
