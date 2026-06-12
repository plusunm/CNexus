"""Semantic Safety v3 — leakage surface mapping over nested signals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Known high-leak semantic node patterns (path suffixes).
HIGH_LEAK_PATTERNS = (
    "winner",
    "precedence_label",
    "confidence_metric",
    "arbitration_result",
    "simulation_result",
    "collapse_detected",
    "collapse_severity_band",
    "risk_observation",
    "risk_classification",
    "recommended_action",
    "simulated_adjustment_label",
    "action",
    "system_responses",
    "counterfactual_observations",
    "violation_score",
    "explainability_retention_metric",
)


@dataclass
class LeakageSurfaceMap:
    level: str
    top_leak_nodes: list[str]
    node_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "top_leak_nodes": self.top_leak_nodes,
            "node_count": self.node_count,
        }


class LeakageSurfaceMapper:
    """Identify which output paths are most likely to be misread."""

    def map_surface(self, signal: dict[str, Any], *, report_label: str = "") -> LeakageSurfaceMap:
        nodes: list[str] = []
        self._collect(signal, report_label, nodes)
        unique = sorted(set(nodes))

        if len(unique) >= 5:
            level = "high"
        elif len(unique) >= 2:
            level = "medium"
        elif unique:
            level = "low"
        else:
            level = "minimal"

        return LeakageSurfaceMap(
            level=level,
            top_leak_nodes=unique[:12],
            node_count=len(unique),
        )

    def _collect(self, node: Any, prefix: str, out: list[str]) -> None:
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            path = f"{prefix}.{key}" if prefix else key
            if key in HIGH_LEAK_PATTERNS:
                out.append(path)
            if isinstance(value, dict):
                self._collect(value, path, out)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._collect(item, f"{path}[{i}]", out)
