"""Annotate spine query events with drift status and confidence."""

from __future__ import annotations

from typing import Any

from core.spine.drift.detector import event_fingerprint
from core.spine.drift.types import DriftReport, DriftStatus


_CONFIDENCE: dict[DriftStatus, float] = {
    "OK": 0.95,
    "MISSING": 0.2,
    "EXTRA": 0.3,
    "SUSPECT": 0.6,
}


class DriftAnnotator:
    def annotate_events(
        self,
        events: list[dict[str, Any]],
        drift: DriftReport,
        *,
        runtime_events: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        missing_fps = {m.fingerprint for m in drift.missing}
        extra_fps = {e.fingerprint for e in drift.extra}
        mismatch_fps = {m.fingerprint for m in drift.mismatch}
        missing_ids = {m.event_id for m in drift.missing if m.event_id}
        extra_ids = {e.event_id for e in drift.extra if e.event_id}
        mismatch_ids = {m.event_id for m in drift.mismatch if m.event_id}

        runtime_ids = {
            str(e.get("event_id"))
            for e in (runtime_events or [])
            if e.get("event_id")
        }

        out: list[dict[str, Any]] = []
        for event in events:
            row = dict(event)
            eid = str(row.get("event_id") or "")
            fp = event_fingerprint(row, side="spine")
            status: DriftStatus = "OK"

            if eid in mismatch_ids or fp in mismatch_fps:
                status = "SUSPECT"
            elif eid in extra_ids or fp in extra_fps:
                status = "EXTRA"
            elif eid in missing_ids or fp in missing_fps:
                status = "MISSING"
            elif runtime_events and eid and eid not in runtime_ids:
                status = "EXTRA"
            elif runtime_events and eid and eid in runtime_ids:
                status = "OK"

            row["drift_status"] = status
            row["confidence"] = _CONFIDENCE[status]
            out.append(row)

        for item in drift.missing:
            if item.event_id and any(str(e.get("event_id")) == item.event_id for e in out):
                continue
            out.append(
                {
                    "event_id": item.event_id or f"runtime-only-{item.fingerprint[:12]}",
                    "event_type": item.type,
                    "trace_id": drift.trace_id,
                    "summary": f"[runtime-only] {item.type}",
                    "drift_status": "MISSING",
                    "confidence": _CONFIDENCE["MISSING"],
                    "source_side": "runtime",
                }
            )

        return out
