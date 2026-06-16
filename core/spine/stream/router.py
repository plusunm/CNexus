"""Execution Spine Stream Router v1 — unified subscription contract for UI."""

from __future__ import annotations

import time
from typing import Any

from core.runtime.execution_tap import get_execution_tap
from core.spine.query.engine import query_by_trace
from core.spine.stream.engine import SpineExplanationStreamEngine

STREAM_CONTRACT_VERSION = "spine-stream-v1"


class ExecutionSpineStreamRouter:
    """Merge spine read + execution tap + explain stream into one push channel."""

    def __init__(self, *, trace_id: str, base_dir: str) -> None:
        self.trace_id = trace_id
        self.base_dir = base_dir
        self.engine = SpineExplanationStreamEngine(trace_id=trace_id)
        self._seen_execution: set[str] = set()

    def connected_message(self) -> dict[str, Any]:
        events = query_by_trace(self.base_dir, self.trace_id, limit=5000)
        tap_rows = get_execution_tap().events_for_trace_merged(self.trace_id)
        return {
            "type": "execution_stream_connected",
            "payload": {
                "connected": True,
                "trace_id": self.trace_id,
                "version": STREAM_CONTRACT_VERSION,
                "channels": ["execution", "causal", "state", "control", "explain"],
                "spine_event_count": len(events),
                "tap_event_count": len(tap_rows),
                "subscription": "active",
            },
        }

    def heartbeat_message(self) -> dict[str, Any]:
        return {
            "type": "execution_stream_heartbeat",
            "payload": {
                "connected": True,
                "trace_id": self.trace_id,
                "version": STREAM_CONTRACT_VERSION,
                "ts": time.time(),
            },
        }

    def poll_messages(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        events = query_by_trace(self.base_dir, self.trace_id, limit=5000)
        spine_ids = {str(e.get("event_id") or "") for e in events if e.get("event_id")}

        for event in events:
            eid = str(event.get("event_id") or "")
            if eid and eid not in self._seen_execution:
                self._seen_execution.add(eid)
                out.append(
                    {
                        "type": "execution_frame",
                        "payload": {
                            "trace_id": self.trace_id,
                            "event_id": eid,
                            "event_type": event.get("event_type"),
                            "summary": event.get("summary"),
                            "timestamp": event.get("timestamp"),
                            "source": "spine",
                        },
                    }
                )
            frame = self.engine.ingest_event(event)
            if frame:
                out.append({"type": "explanation_frame", "payload": frame})

        for tap_row in get_execution_tap().events_for_trace_merged(self.trace_id):
            if tap_row.get("spine_written"):
                continue
            synthetic = {
                "event_id": tap_row.get("event_id")
                or f"tap-{tap_row.get('type')}-{int((tap_row.get('ts') or 0) * 1000)}",
                "trace_id": self.trace_id,
                "event_type": tap_row.get("type"),
                "summary": tap_row.get("summary"),
                "timestamp": tap_row.get("ts"),
                "drift_status": "MISSING",
                "payload": {"source": "execution_tap", **(tap_row.get("payload") or {})},
            }
            eid = str(synthetic["event_id"])
            if eid in spine_ids:
                continue
            if eid not in self._seen_execution:
                self._seen_execution.add(eid)
                out.append(
                    {
                        "type": "execution_frame",
                        "payload": {
                            "trace_id": self.trace_id,
                            "event_id": eid,
                            "event_type": synthetic.get("event_type"),
                            "summary": synthetic.get("summary"),
                            "timestamp": synthetic.get("timestamp"),
                            "source": "execution_tap",
                            "drift_status": "MISSING",
                        },
                    }
                )
            frame = self.engine.ingest_event(synthetic)
            if frame:
                out.append(
                    {
                        "type": "explanation_frame",
                        "payload": frame,
                        "source": "execution_tap",
                    }
                )
        return out

    def snapshot_message(self) -> dict[str, Any]:
        return {
            "type": "explanation_snapshot",
            "payload": self.engine.snapshot_streams(),
        }
