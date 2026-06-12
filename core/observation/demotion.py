"""Semantic demotion map — control-adjacent → observational labels."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Contract-level demotion (extends semantic_safety rename_map)
DEMOTION_MAP: dict[str, str] = {
    "winner": "precedence_label",
    "risk": "observation_band",
    "risk_level": "observation_band",
    "optimization": "simulation_projection",
    "optimize": "simulation_projection",
    "detected": "inferred_signal",
    "collapse_detected": "collapse_indicator",
    "collapse": "collapse_indicator",
    "action": "simulated_adjustment_label",
    "verdict": "stability_projection_metric",
    "confidence": "confidence_metric",
    "arbitration_result": "simulation_result",
}


def _load_output_renames() -> dict[str, str]:
    path = Path(__file__).resolve().parents[1] / "governance" / "semantic_safety" / "rename_map.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return dict(data.get("output_field_renames", {}))
    return {}


OUTPUT_FIELD_DEMOTION: dict[str, str] = {**DEMOTION_MAP, **_load_output_renames()}


def demote_key(key: str) -> str:
    return OUTPUT_FIELD_DEMOTION.get(key, key)


def demote_value(key: str, value: Any) -> Any:
    if key in ("risk", "risk_level") and isinstance(value, str):
        return f"{value}_observation" if not value.endswith("_observation") else value
    return value


def demote_payload(obj: Any) -> Any:
    """Recursively demote keys in dict/list structures (observational projection)."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            nk = demote_key(k)
            out[nk] = demote_value(k, demote_payload(v))
        return out
    if isinstance(obj, list):
        return [demote_payload(x) for x in obj]
    return obj
