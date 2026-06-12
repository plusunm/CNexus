"""Observation event normalizer — strip control semantics, apply demotion."""

from __future__ import annotations

from typing import Any

from core.observation.demotion import demote_payload
from core.observation.schema import CONTROL_STRIP_KEYS, CONTRACT_META, ObservationEvent
from core.governance.semantic_safety.envelope import stamp_observational_safe


class EventNormalizer:
    """Pure transform — no I/O, no runtime calls."""

    def strip_control_fields(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in payload.items() if k not in CONTROL_STRIP_KEYS}

    def normalize(self, event: ObservationEvent) -> ObservationEvent:
        stripped = self.strip_control_fields(event.payload)
        demoted = demote_payload(stripped)
        safe = stamp_observational_safe(demoted, simulation_only=False)
        return ObservationEvent(
            timestamp=event.timestamp,
            source=event.source,
            event_type=event.event_type,
            payload=safe,
            schema_version=event.schema_version,
            envelope={**CONTRACT_META, **event.envelope},
        )

    def normalize_dict(self, raw: dict[str, Any]) -> dict[str, Any]:
        event = ObservationEvent.from_parts(
            source=str(raw.get("source", "unknown")),
            event_type=str(raw.get("event_type", "generic")),
            payload=dict(raw.get("payload") or raw),
        )
        return self.normalize(event).to_dict()
