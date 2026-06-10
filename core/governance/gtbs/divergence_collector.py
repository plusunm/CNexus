"""
GTBS v1.1 P1.5 — shadow divergence observability stream.

Separate from governance cycle audit (Axiom A3/A5). Append-only JSONL;
does not feed CDG or runtime control.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class GTBSShadowDivergenceCollector:
    """Append-only shadow observation log (non-audit, non-actionable)."""

    def __init__(self, base_dir: str | Path) -> None:
        root = Path(base_dir)
        self._dir = root / "observability"
        self._path = self._dir / "gtbs_shadow.jsonl"

    @property
    def path(self) -> Path:
        return self._path

    def record(self, observation: Dict[str, Any]) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(observation, ensure_ascii=False) + "\n")
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


_collector_cache: Dict[str, GTBSShadowDivergenceCollector] = {}


def get_shadow_collector(base_dir: str | Path) -> GTBSShadowDivergenceCollector:
    key = str(Path(base_dir).resolve())
    if key not in _collector_cache:
        _collector_cache[key] = GTBSShadowDivergenceCollector(key)
    return _collector_cache[key]
