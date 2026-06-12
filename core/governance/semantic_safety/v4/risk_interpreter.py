"""Semantic Safety v4 — translate risk vocabulary into observational semantics."""

from __future__ import annotations

from typing import Any


class RiskInterpreter:
    """
    Translate risk-shaped labels into observational language.
    Does not alter numeric measurements — adds interpretation alongside values.
    """

    def interpret_value(self, risk_value: float) -> str:
        if risk_value > 0.7:
            return "high_observational_variance"
        if risk_value > 0.4:
            return "moderate_signal_instability"
        return "stable_observational_field"

    def interpret_label(self, label: str) -> str:
        mapping = {
            "high": "high_observational_variance",
            "medium": "moderate_signal_instability",
            "low": "stable_observational_field",
            "elevated": "high_observational_variance",
            "critical": "high_observational_variance",
            "high_observation": "high_observational_variance",
            "medium_observation": "moderate_signal_instability",
            "low_observation": "stable_observational_field",
            "elevated_observation": "high_observational_variance",
        }
        return mapping.get(label, "observational_field_label")

    def annotate_tree(self, node: Any) -> Any:
        if isinstance(node, dict):
            out: dict[str, Any] = {}
            for key, value in node.items():
                out[key] = self.annotate_tree(value)
                if isinstance(value, (int, float)) and any(
                    token in key for token in ("risk", "score", "severity", "violation", "drift")
                ):
                    out[f"{key}_observational_interpretation"] = self.interpret_value(float(value))
                elif isinstance(value, str) and "risk" in key:
                    out[f"{key}_observational_interpretation"] = self.interpret_label(value)
            return out
        if isinstance(node, list):
            return [self.annotate_tree(item) for item in node]
        return node
