"""
GTBS-L2 — unified multi-source observability snapshot.

S1 Read-Only | S5 Semantic Non-Actuation — snapshot is derived from
observability streams only; never mutates runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GTBSSnapshot:
    """统一 GTBS 多源观测数据的语义快照"""

    timestamp: str = "unknown"
    divergence: dict[str, Any] = field(default_factory=dict)
    shaping: dict[str, Any] = field(default_factory=dict)
    continuity: dict[str, Any] = field(default_factory=dict)
    ecology: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_sources(
        divergence_data: dict[str, Any] | None = None,
        shaping_data: dict[str, Any] | None = None,
        continuity_data: dict[str, Any] | None = None,
        ecology_data: dict[str, Any] | None = None,
    ) -> GTBSSnapshot:
        """聚合多源数据生成语义快照"""
        ts = "unknown"
        for block in (ecology_data, divergence_data, shaping_data, continuity_data):
            if block and block.get("timestamp"):
                ts = str(block["timestamp"])
                break
        return GTBSSnapshot(
            timestamp=ts,
            divergence=divergence_data or {},
            shaping=shaping_data or {},
            continuity=continuity_data or {},
            ecology=ecology_data or {},
        )

    @property
    def is_empty(self) -> bool:
        return not any((self.divergence, self.shaping, self.continuity, self.ecology))
