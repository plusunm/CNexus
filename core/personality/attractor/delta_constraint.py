"""Attractor step-size guard — dampen Σ.S updates (|Δ| ≤ max_step)."""

from __future__ import annotations


def clamp_scalar_step(
    current: float,
    proposed: float,
    *,
    max_step: float = 0.1,
) -> tuple[float, float]:
    """Return (clamped_value, applied_delta) with |applied_delta| ≤ max_step."""
    step = max(0.0, float(max_step))
    delta = float(proposed) - float(current)
    clamped_delta = max(-step, min(step, delta))
    return float(current) + clamped_delta, clamped_delta
