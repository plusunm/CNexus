"""Observation density management — prevent JSONL explosion."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class DensityPolicy:
    max_events_per_hour: int = 3600
    max_events_per_source_hour: int = 1200
    chunk_minutes: int = 5
    downsample_ratio: float = 0.0  # 0 = only chunk merge, no random drop
    enable_chunk_compression: bool = True


@dataclass
class DensityState:
    hour_key: str = ""
    total_count: int = 0
    source_counts: dict[str, int] = field(default_factory=dict)
    chunk_buffers: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hour_key": self.hour_key,
            "total_count": self.total_count,
            "source_counts": self.source_counts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DensityState:
        return cls(
            hour_key=str(data.get("hour_key", "")),
            total_count=int(data.get("total_count", 0)),
            source_counts=dict(data.get("source_counts", {})),
        )


class ObservationDensityManager:
    """Downsample, chunk, and semantically compress observation events before append."""

    def __init__(self, base_dir: str | Path, policy: DensityPolicy | None = None) -> None:
        self.base_dir = Path(base_dir)
        self.policy = policy or DensityPolicy()
        self._state_path = self.base_dir / "observability" / ".density_state.json"
        self._state = self._load_state()

    def _load_state(self) -> DensityState:
        if not self._state_path.exists():
            return DensityState()
        try:
            return DensityState.from_dict(json.loads(self._state_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return DensityState()

    def _save_state(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps(self._state.to_dict(), indent=2), encoding="utf-8")

    @staticmethod
    def _hour_key(ts: str | None = None) -> str:
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%dT%H")
            except ValueError:
                pass
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")

    @staticmethod
    def _chunk_key(source: str, ts: str | None) -> str:
        hour = ObservationDensityManager._hour_key(ts)
        minute_bucket = 0
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                minute_bucket = dt.minute // max(1, 5)  # default 5-min buckets set by caller
            except ValueError:
                pass
        return f"{hour}:{source}:{minute_bucket}"

    def _roll_hour(self, hour_key: str) -> None:
        if self._state.hour_key != hour_key:
            self._state = DensityState(hour_key=hour_key)

    def should_accept(self, *, source: str, timestamp: str | None = None) -> tuple[bool, str]:
        hour_key = self._hour_key(timestamp)
        self._roll_hour(hour_key)
        if self._state.total_count >= self.policy.max_events_per_hour:
            return False, "global_hourly_cap"
        src_count = self._state.source_counts.get(source, 0)
        if src_count >= self.policy.max_events_per_source_hour:
            return False, "source_hourly_cap"
        if self.policy.downsample_ratio > 0:
            digest = hashlib.sha256(f"{source}:{timestamp}:{src_count}".encode()).hexdigest()
            if int(digest[:8], 16) / 0xFFFFFFFF > self.policy.downsample_ratio:
                return False, "downsampled"
        return True, "accepted"

    def record_accepted(self, source: str) -> None:
        self._state.total_count += 1
        self._state.source_counts[source] = self._state.source_counts.get(source, 0) + 1
        self._save_state()

    def compress_chunk(self, events: list[dict[str, Any]], *, source: str) -> dict[str, Any]:
        """Merge a temporal chunk into one summary event (attractor-preserving keys only)."""
        if not events:
            return {}
        timestamps = [e.get("timestamp") for e in events if e.get("timestamp")]
        event_types = [e.get("event_type", "unknown") for e in events]
        payloads = [e.get("payload", e) for e in events]
        memory_chars = [
            int(p.get("memory_context_chars", 0))
            for p in payloads
            if isinstance(p, dict) and p.get("memory_context_chars") is not None
        ]
        return {
            "timestamp": timestamps[-1] if timestamps else datetime.now(timezone.utc).isoformat(),
            "source": source,
            "event_type": "temporal_chunk_summary",
            "payload": {
                "chunk_event_count": len(events),
                "event_types": sorted(set(event_types)),
                "memory_context_chars_mean": round(sum(memory_chars) / len(memory_chars), 2) if memory_chars else 0,
                "observational_only": True,
                "compression": "attractor_preserving_summary",
            },
            "envelope": events[-1].get("envelope", {"observational_only": True}),
        }

    def prepare_for_ingest(self, event: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Returns (events_to_append, meta).
        May return empty list if capped; may buffer for chunk compression.
        """
        source = str(event.get("source", "unknown"))
        ts = event.get("timestamp")
        ok, reason = self.should_accept(source=source, timestamp=ts)
        if not ok:
            return [], {"accepted": False, "reason": reason}

        if not self.policy.enable_chunk_compression:
            self.record_accepted(source)
            return [event], {"accepted": True, "compressed": False}

        chunk_key = self._chunk_key(source, ts)
        buf = self._state.chunk_buffers.setdefault(chunk_key, [])
        buf.append(event)
        # flush when chunk has enough events (>= 10 in same bucket)
        if len(buf) >= 10:
            summary = self.compress_chunk(buf, source=source)
            self._state.chunk_buffers[chunk_key] = []
            self.record_accepted(source)
            return [summary], {"accepted": True, "compressed": True, "chunk_size": len(buf)}

        self.record_accepted(source)
        return [event], {"accepted": True, "compressed": False, "buffered": len(buf)}
