"""Scalar descent monitor — epistemic meta-observer (Axiom 5).

Multi-store epistemic control system contract:
- Tracks potential_v trajectory; does NOT define Lyapunov geometry on canonical Σ.
- Projection-only; advisory control uses separate energy layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("G1.CDG.DescentMonitor")


@dataclass
class DescentSnapshot:
    """Scalar descent check snapshot (epistemic projection, not formal Lyapunov proof)."""

    potential_v: float
    d_v: float
    is_stable: bool
    expected_d_v: float
    actual_d_v: Optional[float] = None
    descent_valid: bool = True
    is_lyapunov_descending: bool = True
    trajectory_stable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "potential_v": round(self.potential_v, 4),
            "d_v": round(self.d_v, 4),
            "is_stable": self.is_stable,
            "is_lyapunov_descending": self.is_lyapunov_descending,
            "trajectory_stable": self.trajectory_stable,
            "expected_d_v": round(self.expected_d_v, 4),
            "actual_d_v": round(self.actual_d_v, 4) if self.actual_d_v is not None else None,
            "descent_valid": self.descent_valid,
        }


class DescentMonitor:
    """Scalar descent heuristic on potential_v trace (meta-observer, non-sovereign)."""

    def __init__(
        self,
        *,
        eps: float = 0.005,
        history_max: int = 128,
        trajectory_var_eps: float = 0.01,
        slope_window: int = 5,
        var_window: int = 10,
    ):
        self.prev_v: Optional[float] = None
        self.eps = eps
        self.descent_eps = eps
        self.history_max = history_max
        self.trajectory_var_eps = trajectory_var_eps
        self.slope_window = slope_window
        self.var_window = var_window
        self._history: List[float] = []

    @property
    def history(self) -> List[float]:
        return list(self._history)

    @property
    def V_trace(self) -> List[float]:
        return self.history

    def register(self, v_t: float) -> Tuple[float, bool]:
        if self.prev_v is None:
            self.prev_v = v_t
            self._append(v_t)
            return 0.0, True

        d_v = v_t - self.prev_v
        self.prev_v = v_t
        self._append(v_t)

        is_stable = self.is_stable(d_v)
        if not is_stable:
            logger.warning("Scalar descent violated: dV=%.4f (eps=%.4f)", d_v, self.eps)

        return d_v, is_stable

    def is_stable(self, d_v: float, eps: Optional[float] = None) -> bool:
        threshold = self.eps if eps is None else eps
        return d_v <= threshold

    def trajectory_stable(self) -> bool:
        trace = self._history
        if len(trace) < self.slope_window:
            return True

        slope = trace[-1] - trace[-self.slope_window]
        window = trace[-min(self.var_window, len(trace)) :]
        arr = np.asarray(window, dtype=float)
        variance = float(np.var(arr))

        deltas = np.diff(arr)
        if len(deltas) >= 2:
            sign_changes = int(np.sum(deltas[1:] * deltas[:-1] < 0))
            crossing_rate = sign_changes / max(1, len(deltas) - 1)
        else:
            crossing_rate = 0.0

        return (
            slope <= self.eps
            and variance < self.trajectory_var_eps
            and crossing_rate < 0.35
        )

    def expected_descent(self, gradient_magnitude: float, step_size: float) -> float:
        return -step_size * (gradient_magnitude ** 2)

    def verify_control_step(
        self,
        v_before: float,
        v_after: float,
        expected_d_v: float,
    ) -> DescentSnapshot:
        actual_d_v = v_after - v_before
        descent_valid = actual_d_v <= max(expected_d_v, 0.0) + self.eps
        d_v, is_lyapunov_descending = self.register(v_after)
        traj_ok = self.trajectory_stable()
        return DescentSnapshot(
            potential_v=v_after,
            d_v=d_v,
            is_stable=self.is_stable(d_v),
            expected_d_v=expected_d_v,
            actual_d_v=actual_d_v,
            descent_valid=descent_valid,
            is_lyapunov_descending=is_lyapunov_descending,
            trajectory_stable=traj_ok,
        )

    def verify_descent(
        self,
        v_before: float,
        v_after: float,
        expected_d_v: float,
    ) -> DescentSnapshot:
        return self.verify_control_step(v_before, v_after, expected_d_v)

    def _append(self, v_t: float) -> None:
        self._history.append(v_t)
        if len(self._history) > self.history_max:
            self._history = self._history[-self.history_max :]


# Backward-compatible aliases (deprecated naming)
LyapunovSnapshot = DescentSnapshot
LyapunovMonitor = DescentMonitor
