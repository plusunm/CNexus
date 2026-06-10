"""L6.5 Stability Energy Layer — structured oscillation + dV/dt phase control."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from core.governance.cdg.control_types import ControlSignal, EnergyGradient
from core.governance.cdg.lyapunov_monitor import DescentMonitor


def oscillation_potential(history: List[int], *, window: int = 5) -> float:
    """
    Control-signal spectral structure — not a scalar counter.

    Decomposes override history into:
    - short-term variance (high-frequency oscillation)
    - long-term mean (low-frequency bias / drift of control)
    - crossing rate (phase instability / bifurcation precursor)
    """
    if len(history) < window:
        return 0.0

    arr = np.asarray(history, dtype=float)
    short = arr[-window:]
    short_var = float(np.var(short))
    long_mean = float(np.mean(arr))
    crossings = sum(1 for i in range(1, len(arr)) if arr[i] != arr[i - 1])
    crossing_rate = crossings / max(1, len(arr) - 1)

    return 0.5 * short_var + 0.3 * long_mean + 0.2 * crossing_rate


@dataclass
class OscillationSpectrum:
    potential: float
    short_var: float
    long_mean: float
    crossing_rate: float
    history_len: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "potential": round(self.potential, 4),
            "short_var": round(self.short_var, 4),
            "long_mean": round(self.long_mean, 4),
            "crossing_rate": round(self.crossing_rate, 4),
            "history_len": self.history_len,
        }


class OscillationSpectrumModel:
    """Time-structured control history — preserves temporal structure for descent heuristics."""

    def __init__(self, *, history_max: int = 64, window: int = 5):
        self.history_max = history_max
        self.window = window
        self.override_history: List[int] = []

    def record(self, signal: int) -> OscillationSpectrum:
        self.override_history.append(int(max(0, min(2, signal))))
        if len(self.override_history) > self.history_max:
            self.override_history = self.override_history[-self.history_max :]
        return self.analyze()

    def analyze(self) -> OscillationSpectrum:
        history = self.override_history
        if len(history) < self.window:
            return OscillationSpectrum(
                potential=0.0,
                short_var=0.0,
                long_mean=0.0,
                crossing_rate=0.0,
                history_len=len(history),
            )

        arr = np.asarray(history, dtype=float)
        short = arr[-self.window :]
        short_var = float(np.var(short))
        long_mean = float(np.mean(arr))
        crossings = sum(1 for i in range(1, len(arr)) if arr[i] != arr[i - 1])
        crossing_rate = crossings / max(1, len(arr) - 1)
        potential = 0.5 * short_var + 0.3 * long_mean + 0.2 * crossing_rate

        return OscillationSpectrum(
            potential=potential,
            short_var=short_var,
            long_mean=long_mean,
            crossing_rate=crossing_rate,
            history_len=len(history),
        )


@dataclass
class EnergySnapshot:
    potential_v: float
    control_phase: str
    ema_rcs: float
    ema_drift: float
    d_v: float
    oscillation: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "potential_v": round(self.potential_v, 4),
            "control_phase": self.control_phase,
            "ema_rcs": round(self.ema_rcs, 4),
            "ema_drift": round(self.ema_drift, 4),
            "d_v": round(self.d_v, 4),
            "oscillation": dict(self.oscillation),
            # backward-compatible aliases
            "osc_energy": round(float(self.oscillation.get("potential", 0.0)), 4),
            "override_count": int(self.oscillation.get("history_len", 0)),
        }


@dataclass
class EnergyStepResult:
    potential_v: float
    d_v: float
    control_phase: str
    snapshot: EnergySnapshot


class StabilityEnergyLayer:
    """
    L6.5 governance energy heuristic — scalar potential V(s) with phase transitions.

    V(s) = (1 - ema_rcs)^2 + (1 + beta) * ema_drift^2 + gamma * oscillation_potential(history)

    This is a bounded governance response metric on projection fields, not a formal
    stability proof on canonical state (Constitutional A1/A6).
    """

    def __init__(
        self,
        *,
        alpha: float = 0.3,
        beta: float = 0.5,
        gamma: float = 1.0,
        stable_threshold: float = 0.3,
        soft_threshold: float = 0.6,
        d_v_soft_threshold: float = 0.02,
        d_v_hard_threshold: float = 0.08,
        lyapunov_eps: float = 0.005,
        history_max: int = 64,
        oscillation_window: int = 5,
        step_soft: float = 0.12,
        step_hard: float = 0.28,
        weaken_factor: float = 0.35,
        trajectory_var_eps: float = 0.01,
        anti_chaos_crossing: float = 0.35,
    ):
        self.ema_rcs = 0.7
        self.ema_drift = 0.1
        self.descent = DescentMonitor(eps=lyapunov_eps, trajectory_var_eps=trajectory_var_eps)
        self.lyapunov = self.descent  # backward-compatible alias

        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.stable_threshold = stable_threshold
        self.soft_threshold = soft_threshold
        self.d_v_soft_threshold = d_v_soft_threshold
        self.d_v_hard_threshold = d_v_hard_threshold
        self.step_soft = step_soft
        self.step_hard = step_hard
        self.weaken_factor = weaken_factor
        self.anti_chaos_crossing = anti_chaos_crossing

        self.oscillation = OscillationSpectrumModel(
            history_max=history_max,
            window=oscillation_window,
        )
        self._last_spectrum = OscillationSpectrum(
            potential=0.0, short_var=0.0, long_mean=0.0, crossing_rate=0.0, history_len=0
        )

    @property
    def _last_potential_v(self) -> Optional[float]:
        return self.lyapunov.prev_v

    @property
    def override_history(self) -> List[int]:
        return self.oscillation.override_history

    def update(
        self,
        raw_rcs: float,
        drift: float,
        override_triggered: bool = False,
        *,
        intervention_signal: Optional[int] = None,
    ) -> float:
        """Update EMA state + control history; return base V (before external boost)."""
        self.ema_rcs = self.alpha * raw_rcs + (1.0 - self.alpha) * self.ema_rcs
        self.ema_drift = self.alpha * drift + (1.0 - self.alpha) * self.ema_drift

        signal = intervention_signal
        if signal is None:
            signal = 2 if override_triggered else 0
        self._last_spectrum = self.oscillation.record(signal)

        return self.compute_potential_v()

    def compute_potential_v(self, oscillation_value: Optional[float] = None) -> float:
        osc = (
            oscillation_value
            if oscillation_value is not None
            else self._last_spectrum.potential
        )
        drift_weight = 1.0 + self.beta
        return (
            (1.0 - self.ema_rcs) ** 2
            + drift_weight * (self.ema_drift ** 2)
            + self.gamma * osc
        )

    def register_potential(self, potential_v: float) -> Tuple[float, bool]:
        """dV/dt via descent monitor — returns (dV, is_descending)."""
        return self.lyapunov.register(potential_v)

    def get_control_phase(
        self,
        potential_v: float,
        d_v: float,
        *,
        trajectory_stable: bool = True,
    ) -> str:
        """
        Dynamical phase — uses V, dV, and trajectory flow consistency.
        """
        if not trajectory_stable:
            if potential_v >= self.soft_threshold:
                return "HARD_OVERRIDE"
            if potential_v >= self.stable_threshold or d_v > self.d_v_soft_threshold:
                return "SOFT_OVERRIDE"

        v_low = potential_v < self.stable_threshold
        v_mid = self.stable_threshold <= potential_v < self.soft_threshold
        v_high = potential_v >= self.soft_threshold

        if v_high and d_v >= self.d_v_hard_threshold:
            return "HARD_OVERRIDE"
        if v_high and d_v > self.d_v_soft_threshold:
            return "HARD_OVERRIDE"
        if v_high:
            return "HARD_OVERRIDE"

        if v_low and d_v <= 0 and trajectory_stable:
            return "STABLE"

        if v_mid or d_v > self.d_v_soft_threshold:
            return "SOFT_OVERRIDE"

        if v_low and d_v > 0:
            return "SOFT_OVERRIDE"

        return "STABLE"

    def compute_control(
        self,
        potential_v: float,
        d_v: float,
        gradient: EnergyGradient,
        *,
        drift_max: float = 0.0,
        drift_tolerance: float = 0.30,
    ) -> ControlSignal:
        """
        Sole control law generator (L6.5) — phase + step + weaken + anti-chaos.
        """
        trajectory_stable = self.lyapunov.trajectory_stable()
        requested = self.get_control_phase(
            potential_v, d_v, trajectory_stable=trajectory_stable
        )

        crossing = self._last_spectrum.crossing_rate
        if not trajectory_stable and crossing > self.anti_chaos_crossing:
            if requested == "HARD_OVERRIDE":
                requested = "SOFT_OVERRIDE"

        if requested == "STABLE" and drift_max > drift_tolerance:
            requested = "SOFT_OVERRIDE"

        mode = requested
        step = 0.0
        weakened = False
        expected_d_v = 0.0

        if mode != "STABLE":
            step = self.step_hard if mode == "HARD_OVERRIDE" else self.step_soft
            expected_d_v = self.lyapunov.expected_descent(gradient.magnitude, step)
            if expected_d_v > 0.0:
                step *= self.weaken_factor
                weakened = True
                if mode == "HARD_OVERRIDE":
                    mode = "SOFT_OVERRIDE"
                else:
                    mode = "STABLE"
                    step = 0.0
                    expected_d_v = 0.0

        return ControlSignal(
            mode=mode,
            step_size=step,
            weakened=weakened,
            requested_phase=requested,
            expected_d_v=expected_d_v,
            trajectory_stable=trajectory_stable,
            gradient=gradient,
        )

    def get_control_phase_legacy(self, potential_v: float, d_v: float) -> str:
        return self.get_control_phase(potential_v, d_v, trajectory_stable=True)

    def step(
        self,
        raw_rcs: float,
        drift: float,
        potential_v: float,
        *,
        override_triggered: bool = False,
        intervention_signal: Optional[int] = None,
    ) -> EnergyStepResult:
        """Full L6.5 step: EMA + spectrum + V + dV + phase."""
        self.update(
            raw_rcs,
            drift,
            override_triggered,
            intervention_signal=intervention_signal,
        )
        d_v, _ = self.register_potential(potential_v)
        phase = self.get_control_phase(potential_v, d_v, trajectory_stable=self.lyapunov.trajectory_stable())
        snapshot = self.snapshot(potential_v, d_v, control_phase=phase)
        return EnergyStepResult(
            potential_v=potential_v,
            d_v=d_v,
            control_phase=phase,
            snapshot=snapshot,
        )

    def snapshot(
        self,
        potential_v: float,
        d_v: float,
        *,
        control_phase: Optional[str] = None,
    ) -> EnergySnapshot:
        phase = control_phase or self.get_control_phase(
            potential_v, d_v, trajectory_stable=self.lyapunov.trajectory_stable()
        )
        return EnergySnapshot(
            potential_v=potential_v,
            control_phase=phase,
            ema_rcs=self.ema_rcs,
            ema_drift=self.ema_drift,
            d_v=d_v,
            oscillation=self._last_spectrum.to_dict(),
        )
