"""CDG Observability — trajectory metrics and audit trail (P4)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from core.governance.cdg.types import AttractorState, CDGCycleRecord, DriftSnapshot


class ObservabilityModule:
    """Ring-buffer telemetry for CDG control-plane cycles."""

    def __init__(self, *, max_records: int = 256):
        self.max_records = max_records
        self._records: List[CDGCycleRecord] = []

    @property
    def records(self) -> List[CDGCycleRecord]:
        return list(self._records)

    def record(
        self,
        *,
        reality: float,
        drift: DriftSnapshot,
        basin: AttractorState,
        state_summary: Dict[str, Any],
        allow: bool,
        reason: str,
        flags: Optional[List[str]] = None,
    ) -> CDGCycleRecord:
        entry = CDGCycleRecord(
            timestamp=datetime.now().isoformat(),
            reality_coupling=reality,
            drift=drift,
            attractor=basin,
            flags=list(flags or []),
            allow=allow,
            reason=reason,
        )
        self._records.append(entry)
        if len(self._records) > self.max_records:
            self._records = self._records[-self.max_records :]
        entry_metrics = entry.to_dict()
        entry_metrics["state"] = state_summary
        return entry

    def trajectory_report(self, last_n: int = 20) -> Dict[str, Any]:
        window = self._records[-last_n:]
        if not window:
            return {
                "count": 0,
                "avg_reality_coupling": None,
                "avg_lock_in_risk": None,
                "interventions": 0,
                "recent": [],
            }

        avg_reality = sum(r.reality_coupling for r in window) / len(window)
        avg_lock_in = sum(r.attractor.lock_in_risk for r in window) / len(window)
        interventions = sum(1 for r in window if not r.allow)

        return {
            "count": len(window),
            "avg_reality_coupling": round(avg_reality, 4),
            "avg_lock_in_risk": round(avg_lock_in, 4),
            "interventions": interventions,
            "latest": window[-1].to_dict(),
            "recent": [r.to_dict() for r in window[-5:]],
        }

    def latest_metrics(self) -> Optional[Dict[str, Any]]:
        if not self._records:
            return None
        return self._records[-1].to_dict()
