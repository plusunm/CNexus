"""L8/G8 influence test — final JSON report."""

from __future__ import annotations

from typing import Any

from core.tests.influence.fixtures import INFLUENCE_TEST_META, MEMORY_DRIFT_SAFE, RESPONSE_DRIFT_SAFE, ROUTING_DRIFT_SAFE


def build_conclusion(metrics: dict[str, float]) -> dict[str, Any]:
    response_d = metrics.get("response_drift", 0.0)
    memory_d = metrics.get("memory_drift", 0.0)
    routing_d = metrics.get("routing_drift", 0.0)

    semantic_leakage = response_d > RESPONSE_DRIFT_SAFE or memory_d > MEMORY_DRIFT_SAFE
    control_leakage = routing_d > ROUTING_DRIFT_SAFE

    if control_leakage:
        confidence = min(1.0, 0.7 + routing_d * 0.3)
        interpretation = ["strong_leakage", "potential_control_coupling"]
    elif semantic_leakage:
        confidence = min(1.0, 0.55 + max(response_d, memory_d))
        interpretation = ["weak_leakage"]
    else:
        confidence = 0.92
        interpretation = ["observational_only_confirmed"]

    return {
        "semantic_leakage": semantic_leakage,
        "control_leakage": control_leakage,
        "confidence": round(confidence, 4),
        "interpretation": interpretation,
    }


def build_report(
    baseline: dict[str, Any],
    injection: dict[str, Any],
    diff: dict[str, Any],
) -> dict[str, Any]:
    metrics = diff["metrics"]
    return {
        "experiment": "L8_G8_influence_test_v1",
        "meta": dict(INFLUENCE_TEST_META),
        "baseline_mode": baseline.get("mode"),
        "injection_mode": injection.get("mode"),
        "result": {
            "response_drift": metrics["response_drift"],
            "memory_drift": metrics["memory_drift"],
            "routing_drift": metrics["routing_drift"],
        },
        "thresholds": {
            "response_drift_safe": RESPONSE_DRIFT_SAFE,
            "memory_drift_safe": MEMORY_DRIFT_SAFE,
            "routing_drift_safe": ROUTING_DRIFT_SAFE,
        },
        "conclusion": build_conclusion(metrics),
        "interpretation": build_conclusion(metrics)["interpretation"],
        "details": {
            "response": diff["response"],
            "memory": diff["memory"],
            "routing": diff["routing"],
            "significant": diff["significant"],
        },
    }
