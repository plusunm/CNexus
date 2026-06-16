"""Runtime ↔ Spine drift detector v1."""

from __future__ import annotations

from typing import Any, Optional

from core.spine.drift.types import (
    SYNC_DRIFTED,
    SYNC_PARTIAL,
    SYNC_SYNCED,
    DriftItem,
    DriftReport,
)


def event_fingerprint(event: dict[str, Any], *, side: str = "spine") -> str:
    """Stable key for cross-source comparison."""
    etype = str(event.get("event_type") or event.get("type") or "unknown")
    eid = event.get("event_id")
    if eid:
        return f"{etype}:{eid}"
    trace = str(event.get("trace_id") or "")
    ts = event.get("timestamp") or event.get("ts")
    summary = str(event.get("summary") or "")[:40]
    return f"{etype}:{trace}:{ts}:{summary}:{side}"


def _normalize_runtime(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": row.get("type") or row.get("event_type"),
        "event_id": row.get("event_id"),
        "trace_id": row.get("trace_id"),
        "timestamp": row.get("ts") or row.get("timestamp"),
        "summary": row.get("summary"),
        "payload": row.get("payload") or {},
        "spine_written": row.get("spine_written", True),
    }


def _normalize_spine(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_type": row.get("event_type") or row.get("type"),
        "event_id": row.get("event_id"),
        "trace_id": row.get("trace_id"),
        "timestamp": row.get("timestamp"),
        "summary": row.get("summary"),
        "payload": row.get("payload") or {},
    }


def _type_mismatch(runtime_ev: dict[str, Any], spine_ev: dict[str, Any]) -> bool:
    rt = str(runtime_ev.get("event_type") or "")
    st = str(spine_ev.get("event_type") or "")
    if rt and st and rt != st:
        return True
    rp = runtime_ev.get("payload") or {}
    sp = spine_ev.get("payload") or {}
    rk = rp.get("kind") or rp.get("caller")
    sk = sp.get("kind") or sp.get("caller")
    if rk and sk and rk != sk:
        return True
    return False


class RuntimeSpineDriftDetector:
    """Compare runtime tap buffer vs spine event log for one trace."""

    def compare(
        self,
        trace_id: str,
        runtime_events: list[dict[str, Any]],
        spine_events: list[dict[str, Any]],
    ) -> DriftReport:
        runtime_norm = [_normalize_runtime(e) for e in runtime_events]
        spine_norm = [_normalize_spine(e) for e in spine_events]

        runtime_by_id: dict[str, dict[str, Any]] = {}
        runtime_no_id: list[dict[str, Any]] = []
        for ev in runtime_norm:
            eid = ev.get("event_id")
            if eid:
                runtime_by_id[str(eid)] = ev
            else:
                runtime_no_id.append(ev)

        spine_by_id: dict[str, dict[str, Any]] = {}
        for ev in spine_norm:
            eid = ev.get("event_id")
            if eid:
                spine_by_id[str(eid)] = ev

        spine_ids = set(spine_by_id)
        runtime_ids = set(runtime_by_id)

        missing: list[DriftItem] = []
        extra: list[DriftItem] = []
        mismatch: list[DriftItem] = []

        for eid in runtime_ids - spine_ids:
            ev = runtime_by_id[eid]
            missing.append(
                DriftItem(
                    fingerprint=f"{ev.get('event_type')}:{eid}",
                    type=str(ev.get("event_type") or "unknown"),
                    event_id=str(eid),
                    trace_id=trace_id,
                    reason="runtime_recorded_spine_missing",
                )
            )

        for eid in spine_ids - runtime_ids:
            ev = spine_by_id[eid]
            extra.append(
                DriftItem(
                    fingerprint=f"{ev.get('event_type')}:{eid}",
                    type=str(ev.get("event_type") or "unknown"),
                    event_id=str(eid),
                    trace_id=trace_id,
                    reason="spine_recorded_runtime_unseen",
                )
            )

        for eid in runtime_ids & spine_ids:
            if _type_mismatch(runtime_by_id[eid], spine_by_id[eid]):
                ev = runtime_by_id[eid]
                mismatch.append(
                    DriftItem(
                        fingerprint=f"{ev.get('event_type')}:{eid}",
                        type=str(ev.get("event_type") or "unknown"),
                        event_id=str(eid),
                        trace_id=trace_id,
                        reason="semantic_mismatch",
                    )
                )

        for ev in runtime_no_id:
            if not ev.get("spine_written", True):
                fp = event_fingerprint(ev, side="runtime")
                missing.append(
                    DriftItem(
                        fingerprint=fp,
                        type=str(ev.get("event_type") or "unknown"),
                        event_id=None,
                        trace_id=trace_id,
                        reason="runtime_only_no_spine_write",
                    )
                )

        last_spine_id: Optional[str] = None
        if spine_norm:
            last = spine_norm[-1]
            last_spine_id = str(last["event_id"]) if last.get("event_id") else None

        matched = len(runtime_ids & spine_ids) - len(mismatch)
        denom = max(1, len(runtime_ids) + len(runtime_no_id))
        score = matched / denom if runtime_norm or spine_norm else 1.0

        if not runtime_norm and not spine_norm:
            sync = SYNC_SYNCED
        elif not missing and not extra and not mismatch:
            sync = SYNC_SYNCED
        elif missing or extra or mismatch:
            sync = SYNC_DRIFTED if score < 0.8 else SYNC_PARTIAL
        else:
            sync = SYNC_PARTIAL

        return DriftReport(
            trace_id=trace_id,
            score=score,
            missing=missing,
            extra=extra,
            mismatch=mismatch,
            runtime_count=len(runtime_norm),
            spine_count=len(spine_norm),
            spine_sync_status=sync,
            last_spine_event_id=last_spine_id,
        )
