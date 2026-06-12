"""Streaming L2 — rolling window cognition over Observation Bus + legacy streams."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from core.governance.gtbs.divergence_analysis import _parse_ts
from core.governance.l2.loader import build_snapshot_from_stream_rows
from core.governance.l2.temporal.temporal_loader import filter_rows_in_window, load_stream_rows, row_timestamp
from core.governance.l2.temporal.window_builder import _aggregate_snapshots, _trend_direction
from core.observation.streaming import ObservationStreamTailer


@dataclass
class StreamingL2Report:
    window_minutes: int
    observation_event_count: int
    snapshot: dict[str, Any]
    online_drift: dict[str, Any]
    rolling_projection: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "report": "CNexus Streaming L2 v0.2",
            "window_minutes": self.window_minutes,
            "observation_event_count": self.observation_event_count,
            "snapshot": self.snapshot,
            "online_drift": self.online_drift,
            "rolling_projection": self.rolling_projection,
            "metadata": self.metadata,
        }

    def render_text(self) -> str:
        drift = self.online_drift
        return "\n".join(
            [
                "=== CNexus Streaming L2 (rolling window) ===",
                f"Window: {self.window_minutes} minutes",
                f"Observation events: {self.observation_event_count}",
                f"Chat turns: {drift.get('chat_turn_count', 0)}",
                f"Event density/hour: {drift.get('events_per_hour', 0):.2f}",
                f"Memory context trend: {drift.get('memory_context_trend', 'n/a')}",
                f"Sources: {', '.join(drift.get('sources', [])) or 'none'}",
                "",
                "(read-only streaming projection — no runtime control)",
            ]
        )


class StreamingL2Window:
    """Rolling semantic window over observation + gtbs streams."""

    def __init__(self, base_dir: str, *, window_minutes: int = 60) -> None:
        self.base_dir = base_dir
        self.window_minutes = window_minutes
        self.tailer = ObservationStreamTailer(base_dir)

    def _window_bounds(self) -> tuple[datetime, datetime]:
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=max(1, self.window_minutes))
        return start, end

    def _filter_observation_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        start, end = self._window_bounds()
        return filter_rows_in_window(rows, start, end)

    def _observation_drift(self, obs_rows: list[dict[str, Any]]) -> dict[str, Any]:
        chat_rows = [r for r in obs_rows if r.get("event_type") == "chat_turn"]
        memory_chars = []
        sources: set[str] = set()
        for row in obs_rows:
            sources.add(str(row.get("source", "unknown")))
            payload = row.get("payload") or {}
            if isinstance(payload, dict) and payload.get("memory_context_chars") is not None:
                memory_chars.append(float(payload["memory_context_chars"]))

        span_hours = max(self.window_minutes / 60.0, 1 / 60.0)
        events_per_hour = len(obs_rows) / span_hours

        trend = "insufficient_data"
        if len(memory_chars) >= 2:
            delta = memory_chars[-1] - memory_chars[0]
            if delta > 50:
                trend = "rising"
            elif delta < -50:
                trend = "falling"
            else:
                trend = "stable"

        return {
            "chat_turn_count": len(chat_rows),
            "events_per_hour": round(events_per_hour, 2),
            "memory_context_trend": trend,
            "memory_context_series": memory_chars[-20:],
            "sources": sorted(sources),
        }

    def build(self, *, poll_new: bool = False) -> StreamingL2Report:
        if poll_new:
            self.tailer.poll_once()

        obs_all = self.tailer.read_window_rows(max_rows=2000)
        obs_window = self._filter_observation_rows(obs_all)

        streams = load_stream_rows(self.base_dir)
        start, end = self._window_bounds()
        shadow_w = filter_rows_in_window(streams["gtbs_shadow"], start, end)
        ecology_w = filter_rows_in_window(streams["ecology_metrics"], start, end)
        singularity_w = filter_rows_in_window(streams["singularity_metrics"], start, end)

        snap = build_snapshot_from_stream_rows(
            self.base_dir,
            shadow_rows=shadow_w,
            ecology_row=ecology_w[-1] if ecology_w else None,
            singularity_row=singularity_w[-1] if singularity_w else None,
        )

        drift = self._observation_drift(obs_window)
        rolling = {
            "observation_density": len(obs_window),
            "shadow_events": len(shadow_w),
            "ecology_points": len(ecology_w),
            "singularity_points": len(singularity_w),
            "proposal_alignment": snap.divergence.get("proposal_alignment"),
            "cpx": snap.ecology.get("cpx"),
        }

        if snap.divergence.get("proposal_alignment") is not None:
            rolling["alignment_band"] = _trend_direction([float(snap.divergence["proposal_alignment"])])

        return StreamingL2Report(
            window_minutes=self.window_minutes,
            observation_event_count=len(obs_window),
            snapshot=asdict(snap),
            online_drift=drift,
            rolling_projection=rolling,
            metadata={
                "observational_only": True,
                "streaming_l2": True,
                "no_runtime_control": True,
            },
        )


def build_streaming_l2_report(
    base_dir: str,
    *,
    window_minutes: int = 60,
    poll_new: bool = False,
) -> StreamingL2Report:
    return StreamingL2Window(base_dir, window_minutes=window_minutes).build(poll_new=poll_new)
