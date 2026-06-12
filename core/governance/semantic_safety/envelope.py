"""Observational safety envelope for CNexus semantic outputs (v2)."""

from __future__ import annotations

from typing import Any

OBSERVATIONAL_SAFETY_V2: dict[str, Any] = {
    "role": "observational_only",
    "non_actionable": True,
    "simulation_only": True,
    "observational_safe": True,
    "semantic_safety_version": "2.0.0",
}


def observational_envelope(*, simulation_only: bool = True) -> dict[str, Any]:
    env = dict(OBSERVATIONAL_SAFETY_V2)
    env["simulation_only"] = simulation_only
    return env


def with_observational_safety(payload: dict[str, Any], *, simulation_only: bool = True) -> dict[str, Any]:
    merged = dict(payload)
    merged.update(observational_envelope(simulation_only=simulation_only))
    return merged


def stamp_observational_safe(payload: dict[str, Any], *, simulation_only: bool = False) -> dict[str, Any]:
    """Apply v2 safety stamp to JSONL / stream records (does not mutate history)."""
    merged = dict(payload)
    merged.setdefault("role", "observational_only")
    merged.setdefault("non_actionable", True)
    merged["observational_safe"] = True
    if simulation_only:
        merged.setdefault("simulation_only", True)
    merged.setdefault("semantic_safety_version", OBSERVATIONAL_SAFETY_V2["semantic_safety_version"])
    return merged


def collapse_severity_band(severity: float) -> str:
    if severity <= 0.3:
        return "none"
    if severity <= 0.5:
        return "moderate"
    if severity <= 0.7:
        return "elevated"
    return "critical"


def risk_observation_label(score: float) -> str:
    if score < 0.3:
        return "low_observation"
    if score < 0.7:
        return "medium_observation"
    return "high_observation"
