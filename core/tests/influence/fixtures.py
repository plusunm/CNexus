"""L8/G8 influence test — shared fixtures and synthetic signals."""

from __future__ import annotations

from typing import Any

STANDARD_CHAT_INPUTS: list[str] = [
    "What is my current goal focus?",
    "Summarize what you know about project CNexus.",
    "Remember that observational-only is a hard constraint.",
    "Recall the last constraint we discussed.",
]

DEFAULT_L8_SIGNALS: dict[str, Any] = {
    "collapse_score": 0.72,
    "field_instability": 0.61,
    "attractor_pressure": 0.58,
    "temporal_coherence": "broken",
    "source": "influence_test_stimulus",
    "observational_only": True,
}

DEFAULT_G8_SIGNALS: dict[str, Any] = {
    "governance_pressure": 0.67,
    "meta_stability_index": 0.44,
    "control_surfaces_active": False,
    "source": "influence_test_stimulus",
    "observational_only": True,
}

INFLUENCE_TEST_META: dict[str, bool] = {
    "observational_only": True,
    "no_runtime_mutation": True,
    "no_control_assumption": True,
    "shadow_execution": True,
}

# Thresholds from spec v1
RESPONSE_DRIFT_SAFE = 0.05
MEMORY_DRIFT_SAFE = 0.10
ROUTING_DRIFT_SAFE = 0.0
