"""Runtime ↔ Spine drift report types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

DriftStatus = Literal["OK", "MISSING", "EXTRA", "SUSPECT"]

SYNC_PARTIAL = "partial"
SYNC_SYNCED = "synced"
SYNC_DRIFTED = "drifted"


@dataclass
class DriftItem:
    fingerprint: str
    type: str
    event_id: Optional[str] = None
    trace_id: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "type": self.type,
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "reason": self.reason,
        }


@dataclass
class DriftReport:
    trace_id: str
    score: float
    missing: list[DriftItem] = field(default_factory=list)
    extra: list[DriftItem] = field(default_factory=list)
    mismatch: list[DriftItem] = field(default_factory=list)
    runtime_count: int = 0
    spine_count: int = 0
    spine_sync_status: str = SYNC_PARTIAL
    last_spine_event_id: Optional[str] = None

    @property
    def missing_count(self) -> int:
        return len(self.missing)

    @property
    def extra_count(self) -> int:
        return len(self.extra)

    @property
    def mismatch_count(self) -> int:
        return len(self.mismatch)

    def summary(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "missing_count": self.missing_count,
            "extra_count": self.extra_count,
            "mismatch_count": self.mismatch_count,
            "runtime_count": self.runtime_count,
            "spine_count": self.spine_count,
            "spine_sync_status": self.spine_sync_status,
            "last_spine_event_id": self.last_spine_event_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            **self.summary(),
            "missing": [m.to_dict() for m in self.missing],
            "extra": [e.to_dict() for e in self.extra],
            "mismatch": [m.to_dict() for m in self.mismatch],
        }
