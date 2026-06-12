"""L8/G8 influence test — drift metric helpers."""

from __future__ import annotations

import difflib
from typing import Any


def _ratio(a: str, b: str) -> float:
    if a == b:
        return 0.0
    if not a and not b:
        return 0.0
    return round(1.0 - difflib.SequenceMatcher(None, a, b).ratio(), 4)


def response_drift_score(baseline_responses: list[str], test_responses: list[str]) -> float:
    if not baseline_responses and not test_responses:
        return 0.0
    n = max(len(baseline_responses), len(test_responses), 1)
    scores = []
    for i in range(n):
        a = baseline_responses[i] if i < len(baseline_responses) else ""
        b = test_responses[i] if i < len(test_responses) else ""
        scores.append(_ratio(a, b))
    return round(sum(scores) / len(scores), 4)


def memory_drift_score(baseline_trace: list[dict[str, Any]], test_trace: list[dict[str, Any]]) -> float:
    if not baseline_trace and not test_trace:
        return 0.0
    n = max(len(baseline_trace), len(test_trace), 1)
    deltas: list[float] = []
    for i in range(n):
        b = baseline_trace[i] if i < len(baseline_trace) else {}
        t = test_trace[i] if i < len(test_trace) else {}
        parts: list[float] = []
        if b.get("denied") != t.get("denied"):
            parts.append(1.0)
        imp_b = float(b.get("importance", 0))
        imp_t = float(t.get("importance", 0))
        parts.append(abs(imp_b - imp_t))
        if b.get("layer") != t.get("layer"):
            parts.append(0.5)
        if b.get("role") != t.get("role"):
            parts.append(0.5)
        deltas.append(min(1.0, sum(parts) / max(len(parts), 1)))
    return round(sum(deltas) / len(deltas), 4)


def routing_drift_score(baseline_trace: list[dict[str, Any]], test_trace: list[dict[str, Any]]) -> float:
    if not baseline_trace and not test_trace:
        return 0.0
    n = max(len(baseline_trace), len(test_trace), 1)
    mismatches = 0
    for i in range(n):
        b = baseline_trace[i] if i < len(baseline_trace) else {}
        t = test_trace[i] if i < len(test_trace) else {}
        keys = ("pipeline", "runtime_mode", "recall_path", "capture_path", "use_memory")
        if any(b.get(k) != t.get(k) for k in keys):
            mismatches += 1
    return round(mismatches / n, 4)
