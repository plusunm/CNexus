"""L8/G8 influence test — behavioral diff engine."""

from __future__ import annotations

from typing import Any

from core.tests.influence.fixtures import MEMORY_DRIFT_SAFE, RESPONSE_DRIFT_SAFE, ROUTING_DRIFT_SAFE
from core.tests.influence.metrics import memory_drift_score, response_drift_score, routing_drift_score


class DiffAnalyzer:
    def compute_response_delta(self, baseline: dict[str, Any], test: dict[str, Any]) -> dict[str, Any]:
        score = response_drift_score(baseline.get("responses", []), test.get("responses", []))
        pairs = []
        for i, (a, b) in enumerate(zip(baseline.get("responses", []), test.get("responses", []))):
            pairs.append({"turn": i, "equal": a == b})
        return {"drift_score": score, "pairs": pairs, "safe_threshold": RESPONSE_DRIFT_SAFE}

    def compute_memory_delta(self, baseline: dict[str, Any], test: dict[str, Any]) -> dict[str, Any]:
        score = memory_drift_score(baseline.get("memory_trace", []), test.get("memory_trace", []))
        return {"drift_score": score, "safe_threshold": MEMORY_DRIFT_SAFE}

    def compute_routing_delta(self, baseline: dict[str, Any], test: dict[str, Any]) -> dict[str, Any]:
        score = routing_drift_score(baseline.get("routing_trace", []), test.get("routing_trace", []))
        mismatches = []
        for i, (b, t) in enumerate(zip(baseline.get("routing_trace", []), test.get("routing_trace", []))):
            if b != t:
                mismatches.append({"index": i, "baseline": b, "test": t})
        return {
            "drift_score": score,
            "mismatches": mismatches,
            "safe_threshold": ROUTING_DRIFT_SAFE,
        }

    def analyze(self, baseline: dict[str, Any], test: dict[str, Any]) -> dict[str, Any]:
        response = self.compute_response_delta(baseline, test)
        memory = self.compute_memory_delta(baseline, test)
        routing = self.compute_routing_delta(baseline, test)
        metrics = {
            "response_drift": response["drift_score"],
            "memory_drift": memory["drift_score"],
            "routing_drift": routing["drift_score"],
        }
        return {
            "response": response,
            "memory": memory,
            "routing": routing,
            "metrics": metrics,
            "significant": self.is_significant(metrics),
        }

    def is_significant(self, metrics: dict[str, float]) -> bool:
        return (
            metrics.get("response_drift", 0) > RESPONSE_DRIFT_SAFE
            or metrics.get("memory_drift", 0) > MEMORY_DRIFT_SAFE
            or metrics.get("routing_drift", 0) > ROUTING_DRIFT_SAFE
        )
