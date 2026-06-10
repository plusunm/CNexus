"""
GTBS-L2 v0.2 — temporal window data structures.

S6 No Temporal Governance | S7 No Control Leakage
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.l2.snapshot import GTBSSnapshot


@dataclass
class L2TemporalWindow:
    start_ts: str
    end_ts: str
    window_days: int = 7
    snapshots: list[GTBSSnapshot] = field(default_factory=list)
    aggregated: dict[str, Any] = field(default_factory=dict)

    @property
    def snapshot_count(self) -> int:
        return len(self.snapshots)


@dataclass
class L2TemporalReport:
    time_range: str
    narrative_version: str = "L2_v0.2"
    temporal_summaries: dict[str, str] = field(default_factory=dict)
    trend_signals: dict[str, Any] = field(default_factory=dict)
    raw_window: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report": "GTBS-L2 v0.2 Temporal Report",
            "time_range": self.time_range,
            "narrative_version": self.narrative_version,
            "temporal_summaries": self.temporal_summaries,
            "trend_signals": self.trend_signals,
            "raw_window": self.raw_window,
            "metadata": self.metadata,
        }
