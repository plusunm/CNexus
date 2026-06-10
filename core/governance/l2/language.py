"""GTBS-L2 semantic vocabulary — unified classification helpers."""

from __future__ import annotations


def _classify(value: float, thresholds: tuple[float, float]) -> str:
    low, high = thresholds
    v = max(0.0, min(float(value), 1.0))
    if v < low:
        return "low"
    if v < high:
        return "medium"
    return "high"


def classify_openness(score: float) -> str:
    """Higher score = more openness retained (inverse of ODC decay)."""
    return _classify(score, (0.3, 0.7))


def classify_reality_coupling(score: float) -> str:
    return _classify(score, (0.3, 0.7))


def classify_risk(score: float) -> str:
    return _classify(score, (0.3, 0.7))
