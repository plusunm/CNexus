"""Feedback loop — observation only by default (no runtime mutation)."""

from __future__ import annotations

from typing import Any


class ExplanationEvaluator:
    def evaluate(self, frame: dict[str, Any]) -> dict[str, Any]:
        score = 0.0
        if frame.get("causal_delta", {}).get("added_edges"):
            score += 0.3
        if frame.get("state_delta", {}).get("delta"):
            score += 0.3
        if frame.get("control_delta"):
            score += 0.4
        return {"score": round(score, 2), "quality": "HIGH" if score > 0.7 else "LOW"}


class DriftDetector:
    def detect(self, event: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
        drift: dict[str, Any] = {}
        etype = str(event.get("event_type") or "")
        if etype in ("recall", "capture") and not frame.get("causal_delta", {}).get("added_edges"):
            drift["missing_causal"] = True
        if etype == "control" and not frame.get("control_delta"):
            drift["missing_control"] = True
        if etype == "state" and not frame.get("state_delta", {}).get("delta"):
            drift["missing_state"] = True
        return drift


class ControlAdjuster:
    """Returns suggested control_state — not applied to runtime unless explicitly enabled."""

    def adjust(self, drift: dict[str, Any], control_state: dict[str, Any]) -> dict[str, Any]:
        state = dict(control_state)
        if drift.get("missing_control"):
            state["strict_mode"] = True
        if drift.get("missing_causal"):
            state["trace_enforcement"] = True
        if drift.get("missing_state"):
            state["state_diff_enforcement"] = True
        return state


class SpineFeedbackLoopEngine:
    def __init__(self) -> None:
        self.evaluator = ExplanationEvaluator()
        self.drift = DriftDetector()
        self.adjuster = ControlAdjuster()
        self.control_state: dict[str, Any] = {
            "strict_mode": False,
            "trace_enforcement": False,
            "state_diff_enforcement": False,
        }

    def process(self, event: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
        evaluation = self.evaluator.evaluate(frame)
        drift_report = self.drift.detect(event, frame)
        self.control_state = self.adjuster.adjust(drift_report, self.control_state)
        return {
            "evaluation": evaluation,
            "drift": drift_report,
            "control_state": dict(self.control_state),
            "applied_to_runtime": False,
            "heal_actions": self._heal_actions(drift_report, event),
        }

    def _heal_actions(self, drift: dict[str, Any], event: dict[str, Any]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        eid = str(event.get("event_id") or "")
        if drift.get("missing_causal"):
            actions.append({"action": "backfill_causal", "event_id": eid})
        if drift.get("missing_control"):
            actions.append({"action": "backfill_control", "event_id": eid})
        if drift.get("missing_state"):
            actions.append({"action": "backfill_state", "event_id": eid})
        return actions
