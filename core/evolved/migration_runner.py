"""Layer 6 migration_engine — read-only SANDBOX mapping IR executor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_DEFAULT_IR = (
    Path(__file__).resolve().parents[2] / "docs" / "evolved" / "step_01_mapping_table.ref.json"
)


class MigrationRunner:
    """Deterministic mapping lookup — no embedded remap logic, IR only."""

    def __init__(self, ir_path: Optional[str | Path] = None):
        self.ir_path = Path(ir_path) if ir_path else _DEFAULT_IR
        self._ir: Dict[str, Any] = {}
        self._by_target: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.ir_path.exists():
            return
        self._ir = json.loads(self.ir_path.read_text(encoding="utf-8"))
        for row in self._ir.get("mappings") or []:
            target = str(row.get("target") or "")
            if target:
                self._by_target[target] = row

    @property
    def total_mappings(self) -> int:
        return int(self._ir.get("total_mappings") or len(self._by_target))

    @property
    def classification_summary(self) -> Dict[str, Any]:
        return dict(self._ir.get("classification_summary") or {})

    def lookup_target(self, target: str) -> Optional[Dict[str, Any]]:
        return self._by_target.get(target)

    def lookup_source(self, source: str) -> List[Dict[str, Any]]:
        return [
            row
            for row in (self._ir.get("mappings") or [])
            if str(row.get("source")) == source
        ]

    def factory_gaps(self) -> List[Dict[str, Any]]:
        return [
            row
            for row in (self._ir.get("mappings") or [])
            if str(row.get("classification")) == "factory_gap"
        ]

    def summary(self) -> Dict[str, Any]:
        return {
            "ir_path": str(self.ir_path),
            "loaded": bool(self._ir),
            "total_mappings": self.total_mappings,
            "classification_summary": self.classification_summary,
            "factory_gap_count": len(self.factory_gaps()),
        }
