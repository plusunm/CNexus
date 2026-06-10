"""
Phase B — singularity metrics observability stream (independent from audit).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.governance.singularity.metrics import (
    SingularityMetricsEngine,
    SingularityMetricsSnapshot,
)


class SingularityMetricsCollector:
    """Append-only singularity_metrics.jsonl — never merged into governance audit."""

    def __init__(self, base_dir: str | Path) -> None:
        root = Path(base_dir)
        self._dir = root / "observability"
        self._path = self._dir / "singularity_metrics.jsonl"

    @property
    def path(self) -> Path:
        return self._path

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

    def record(self, snapshot: SingularityMetricsSnapshot) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(snapshot.to_dict(), ensure_ascii=False) + "\n")
        return self._path

    def record_snapshot(self, base_dir: str | Path | None = None) -> SingularityMetricsSnapshot:
        """Compute current metrics and append to singularity stream."""
        root = str(base_dir) if base_dir is not None else str(self._dir.parent)
        snapshot = SingularityMetricsEngine(root).compute()
        self.record(snapshot)
        return snapshot
