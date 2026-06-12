"""Semantic Safety v4 — downgrade control-projecting keys (presentation layer)."""

from __future__ import annotations

import copy
from typing import Any

KEY_PROJECTION_MAP: dict[str, str] = {
    "winner": "simulated_precedence_observation",
    "decision": "non_actionable_classification",
    "risk": "observational_signal",
    "risk_classification": "observational_signal_band",
    "risk_observation": "observational_signal_band",
    "recommended_action": "archived_non_actionable_note",
    "collapse_detected": "collapse_severity_observation",
    "system_responses": "counterfactual_observations",
    "action": "simulated_adjustment_observation",
    "arbitration_result": "simulation_observation",
}

VALUE_PROJECTION_MAP: dict[str, str] = {
    "high": "elevated_observation",
    "medium": "moderate_observation",
    "low": "low_observation",
    "elevated": "elevated_observation",
    "critical": "critical_observation",
}


class ControlProjectionBlocker:
    """Rename control-projecting fields for safe external presentation."""

    def block(self, signal: dict[str, Any]) -> tuple[dict[str, Any], int]:
        sanitized = copy.deepcopy(signal)
        counter = [0]
        self._walk(sanitized, counter)
        return sanitized, counter[0]

    def _walk(self, node: Any, counter: list[int]) -> None:
        if not isinstance(node, dict):
            return
        renames: dict[str, Any] = {}
        for key, value in list(node.items()):
            new_key = KEY_PROJECTION_MAP.get(key, key)
            if new_key != key:
                counter[0] += 1
            if isinstance(value, str) and value in VALUE_PROJECTION_MAP:
                value = VALUE_PROJECTION_MAP[value]
            elif isinstance(value, dict):
                self._walk(value, counter)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        self._walk(item, counter)
            renames[new_key] = value
        node.clear()
        node.update(renames)
