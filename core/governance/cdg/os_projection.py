"""Runtime OS → RealityManifold readonly projection adapter."""

from __future__ import annotations

from typing import Any, Dict, List

from core.governance.cdg.reality_manifold import RealityFrame, RealityManifold


def frames_from_os_events(
    events: List[Dict[str, Any]],
    *,
    source: str = "runtime_os",
) -> List[RealityFrame]:
    """Map external Runtime OS replay/telemetry events into RealityFrames."""
    frames: List[RealityFrame] = []
    for raw in events:
        if not raw:
            continue
        payload = dict(raw.get("payload") or {})
        if "text" not in payload and raw.get("text"):
            payload["text"] = raw["text"]
        payload.setdefault("event_type", str(raw.get("event_type", "os_event")))
        frames.append(
            RealityFrame(
                event_id=str(raw.get("event_id") or raw.get("id")),
                parent_id=raw.get("parent_id"),
                payload=payload,
                timestamp=float(raw.get("timestamp", 0.0)),
                source=str(raw.get("source", source)),
            )
        )
    return frames


def ingest_os_projection(
    manifold: RealityManifold,
    events: List[Dict[str, Any]],
    *,
    source: str = "runtime_os",
) -> int:
    """Batch ingest readonly OS projection; returns count ingested."""
    if not events:
        return 0
    manifold.ingest_os_events(
        [{**raw, "source": raw.get("source", source)} for raw in events if raw]
    )
    return len(events)
