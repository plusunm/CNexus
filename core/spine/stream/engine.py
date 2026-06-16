"""Real-time explanation stream engine (CP-2.5)."""

from __future__ import annotations

from typing import Any

from core.spine.execution.bind_v2 import build_frame_execution_bind
from core.spine.execution.semantics import classify_event_phase
from core.spine.feedback.loop import SpineFeedbackLoopEngine
from core.spine.stream.builders import IncrementalCausalBuilder
from core.spine.stream.control_tracker import ControlAttributionStream
from core.spine.stream.narrative import StreamingNarrativeEngine
from core.spine.stream.state_tracker import LiveStateDiffTracker

STREAM_VERSION = "explain-stream-v2"


class SpineExplanationStreamEngine:
    def __init__(self, *, trace_id: str) -> None:
        self.trace_id = trace_id
        self.causal_builder = IncrementalCausalBuilder()
        self.state_tracker = LiveStateDiffTracker()
        self.control_tracker = ControlAttributionStream()
        self.narrator = StreamingNarrativeEngine()
        self.feedback_engine = SpineFeedbackLoopEngine()
        self._seen: set[str] = set()
        self._events: list[dict[str, Any]] = []

    def ingest_event(self, event: dict[str, Any]) -> dict[str, Any] | None:
        eid = str(event.get("event_id") or "")
        if not eid or eid in self._seen:
            return None
        if str(event.get("trace_id") or "") != self.trace_id:
            return None
        self._seen.add(eid)
        self._events.append(dict(event))

        causal_delta = self.causal_builder.update(event)
        state_delta = self.state_tracker.update(event)
        control_delta = self.control_tracker.update(event)
        narrative_delta = self.narrator.update(
            event=event,
            causal_delta=causal_delta,
            state_delta=state_delta,
            control_delta=control_delta,
        )

        frame: dict[str, Any] = {
            "version": STREAM_VERSION,
            "trace_id": self.trace_id,
            "event_id": eid,
            "frame_type": "incremental_explanation",
            "execution_phase": classify_event_phase(event),
            "execution_bind": build_frame_execution_bind(self.trace_id, self._events, eid),
            "causal_delta": causal_delta,
            "state_delta": state_delta,
            "control_delta": control_delta,
            "narrative_delta": narrative_delta,
        }
        frame["feedback"] = self.feedback_engine.process(event, frame)
        heal_actions = []
        fb_drift = frame["feedback"].get("drift") or {}
        if fb_drift.get("missing_causal"):
            heal_actions.append({"action": "backfill_causal", "event_id": eid})
        if fb_drift.get("missing_state"):
            heal_actions.append({"action": "backfill_state", "event_id": eid})
        if heal_actions:
            frame["heal_suggestions"] = heal_actions

        drift_status = event.get("drift_status")
        if drift_status and drift_status != "OK":
            frame["explain_v3_hint"] = {
                "caveat": f"Event marked {drift_status} in drift overlay",
                "confidence": event.get("confidence"),
            }
        return frame

    def snapshot_streams(self) -> dict[str, Any]:
        return {
            "causal_graph": self.causal_builder.graph,
            "state_projection": self.state_tracker._projection,
            "control_state": self.feedback_engine.control_state,
        }
