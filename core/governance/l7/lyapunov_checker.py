"""L7 — scalar descent heuristic checker (report channel; not formal proof)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Union

import numpy as np

from core.governance.l7.transition_reconstructor import StateVector


@dataclass
class LyapunovCheckResult:
    lyapunov_margin: float
    lyapunov_descent_ratio: float
    lyapunov_violations: int
    alpha: float
    eps: float
    energy_channel: str

    def to_dict(self) -> dict:
        return {
            "lyapunov_margin": round(self.lyapunov_margin, 6),
            "lyapunov_descent_ratio": round(self.lyapunov_descent_ratio, 4),
            "lyapunov_violations": self.lyapunov_violations,
            "alpha": self.alpha,
            "eps": self.eps,
            "energy_channel": self.energy_channel,
        }


@dataclass
class DualLyapunovCheckResult:
    """Scalar channel drives verdict; composite is report-only."""

    scalar: LyapunovCheckResult
    composite: LyapunovCheckResult

    def to_dict(self) -> dict:
        return {
            "scalar": self.scalar.to_dict(),
            "composite": self.composite.to_dict(),
        }


class LyapunovInequalityChecker:
    """
    Discrete descent heuristic on potential_v (audit projection scalar):

        ΔV ≤ −α·V² + ε

    Field names retain ``lyapunov_*`` for audit compatibility. This is epistemic
    reconstruction / projection consistency monitoring — not Lyapunov stability proof.
    """

    def __init__(self, *, alpha: float = 0.01, eps: float = 0.005):
        self.alpha = alpha
        self.eps = eps

    def check(
        self,
        series: Sequence[Union[float, StateVector]],
        *,
        energy_channel: str = "potential_v",
    ) -> LyapunovCheckResult:
        v = self._energy_series(series, energy_channel=energy_channel)
        if len(v) < 2:
            return LyapunovCheckResult(
                lyapunov_margin=1.0,
                lyapunov_descent_ratio=1.0,
                lyapunov_violations=0,
                alpha=self.alpha,
                eps=self.eps,
                energy_channel=energy_channel,
            )

        arr = np.asarray(v, dtype=float)
        d_v = np.diff(arr)
        v_sq = np.maximum(arr[:-1] ** 2, 1e-6)
        bound = -self.alpha * v_sq + self.eps
        satisfied = d_v <= bound
        margin_slack = bound - d_v

        return LyapunovCheckResult(
            lyapunov_margin=float(np.mean(margin_slack)),
            lyapunov_descent_ratio=float(np.mean(satisfied)),
            lyapunov_violations=int(np.sum(~satisfied)),
            alpha=self.alpha,
            eps=self.eps,
            energy_channel=energy_channel,
        )

    @staticmethod
    def _energy_series(
        series: Sequence[Union[float, StateVector]],
        *,
        energy_channel: str,
    ) -> List[float]:
        out: List[float] = []
        for item in series:
            if isinstance(item, StateVector):
                if energy_channel == "composite":
                    out.append(item.potential_v + 0.25 * item.norm_sq())
                else:
                    out.append(item.potential_v)
            else:
                out.append(float(item))
        return out

    def check_dual_from_records(self, records: List[dict]) -> DualLyapunovCheckResult:
        vectors = [StateVector.from_record(r) for r in records]
        scalar_v = [sv.potential_v for sv in vectors]
        return DualLyapunovCheckResult(
            scalar=self.check(scalar_v, energy_channel="potential_v"),
            composite=self.check(vectors, energy_channel="composite"),
        )

    def check_from_records(self, records: List[dict]) -> LyapunovCheckResult:
        """Verdict channel — scalar potential_v only."""
        return self.check_dual_from_records(records).scalar
