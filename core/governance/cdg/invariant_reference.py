"""L6.7 Invariant Reference Manifold — CCEDS v4.0 (exogenous anchor + anti-collapse)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class ReferencePoint:
    """Non-optimizable reference manifold sample S_ref."""

    v_ref: float
    drift_ref: float
    rcs_ref: float
    external_v: float
    internal_v: float
    alpha: float
    entropy: float
    lag_used: int
    source: str = "mixed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "v_ref": round(self.v_ref, 4),
            "drift_ref": round(self.drift_ref, 4),
            "rcs_ref": round(self.rcs_ref, 4),
            "external_v": round(self.external_v, 4),
            "internal_v": round(self.internal_v, 4),
            "alpha": round(self.alpha, 4),
            "entropy": round(self.entropy, 4),
            "lag_used": self.lag_used,
            "source": self.source,
        }


class InvariantReferenceManifold:
    """
    CCEDS v4.0 reference anchor.

    S_ref(t) = α · S_internal(t − k) + (1 − α) · S_external

    Guards:
    - lag separation (k ≥ 3) decouples control/verify correlation
    - external dominance (strength > θ) → α → α_min
    - entropy floor H(S_ref) > ε prevents reference collapse
    """

    DEFAULT_EXTERNAL = {"v": 0.0, "drift": 0.0, "rcs": 0.7, "strength": 0.0}

    def __init__(
        self,
        *,
        alpha: float = 0.3,
        alpha_min: float = 0.1,
        lag: int = 5,
        internal_max: int = 50,
        external_max: int = 50,
        external_dominance_theta: float = 0.5,
        entropy_floor: float = 0.05,
        exogenous_default_v: float = 0.0,
        exogenous_default_drift: float = 0.0,
        exogenous_default_rcs: float = 0.7,
    ):
        self.alpha = alpha
        self.alpha_min = alpha_min
        self.lag = max(3, lag)
        self.internal_max = internal_max
        self.external_max = external_max
        self.external_dominance_theta = external_dominance_theta
        self.entropy_floor = entropy_floor
        self.exogenous_default_v = exogenous_default_v
        self.exogenous_default_drift = exogenous_default_drift
        self.exogenous_default_rcs = exogenous_default_rcs
        self.internal_buffer: List[Dict[str, float]] = []
        self.external_buffer: List[Dict[str, float]] = []

    # --- backward-compatible aliases ---
    @property
    def internal_snapshots(self) -> List[Dict[str, float]]:
        return self.internal_buffer

    @property
    def external_stream(self) -> List[Dict[str, float]]:
        return self.external_buffer

    def ingest_internal(self, state: Dict[str, Any]) -> None:
        self.internal_buffer.append(self._normalize_state(state))
        if len(self.internal_buffer) > self.internal_max:
            self.internal_buffer.pop(0)

    def take_internal_snapshot(self, state: Dict[str, Any]) -> None:
        """Backward-compatible alias."""
        self.ingest_internal(state)

    def ingest_external(self, signal: Dict[str, Any]) -> None:
        entry = self._normalize_external(signal)
        self.external_buffer.append(entry)
        if len(self.external_buffer) > self.external_max:
            self.external_buffer.pop(0)

    @staticmethod
    def _normalize_state(state: Dict[str, Any]) -> Dict[str, float]:
        return {
            "v": float(state.get("potential_v", state.get("v", 0.0))),
            "drift": float(state.get("drift", 0.0)),
            "rcs": float(state.get("rcs", 0.0)),
        }

    @staticmethod
    def _normalize_external(signal: Dict[str, Any]) -> Dict[str, float]:
        raw_strength = signal.get("strength")
        if raw_strength is None:
            raw_strength = 1.0 if signal.get("source") in ("user_action", "runtime_os") else 0.5
        return {
            "v": float(signal.get("v", signal.get("signal", 0.0))),
            "drift": float(signal.get("drift", 0.0)),
            "rcs": float(signal.get("rcs", 0.7)),
            "strength": float(raw_strength),
        }

    @staticmethod
    def event_to_anchor(raw: Dict[str, Any], *, source: str = "runtime_os") -> Dict[str, Any]:
        event_type = str(raw.get("event_type", "os_event"))
        payload = raw.get("payload") or {}
        v_signal = float(raw.get("v", payload.get("v", payload.get("signal", 0.0))))

        if v_signal == 0.0:
            if event_type in ("user_action", "grounded_action"):
                v_signal = 0.0
            elif event_type in ("os_event", "replay", "telemetry"):
                v_signal = 0.05
            elif event_type in ("alert", "anomaly", "drift_alert"):
                v_signal = 0.35

        return {
            "v": v_signal,
            "drift": float(raw.get("drift", payload.get("drift", 0.0))),
            "rcs": float(raw.get("rcs", payload.get("rcs", 0.7))),
            "strength": float(raw.get("strength", 0.8 if source == "runtime_os" else 1.0)),
            "source": source,
            "event_type": event_type,
            "event_id": raw.get("event_id") or raw.get("id"),
        }

    def ingest_user_action_anchor(self, event_id: str, text: str = "") -> None:
        self.ingest_external(
            {
                "v": 0.0,
                "drift": 0.0,
                "rcs": 0.85,
                "strength": 1.0,
                "source": "user_action",
                "event_id": event_id,
                "text_len": len(text),
            }
        )

    def _lagged_internal(self) -> Optional[Dict[str, float]]:
        if not self.internal_buffer:
            return None
        if len(self.internal_buffer) <= self.lag:
            return dict(self.internal_buffer[0])
        return dict(self.internal_buffer[-(self.lag + 1)])

    def _latest_external(self) -> Dict[str, float]:
        if not self.external_buffer:
            return {
                "v": self.exogenous_default_v,
                "drift": self.exogenous_default_drift,
                "rcs": self.exogenous_default_rcs,
                "strength": 0.0,
            }
        return dict(self.external_buffer[-1])

    def _effective_alpha(self, external: Dict[str, float]) -> float:
        strength = float(external.get("strength", 0.0))
        if strength > self.external_dominance_theta:
            return self.alpha_min
        return self.alpha

    def _reference_entropy(
        self,
        internal: Dict[str, float],
        external: Dict[str, float],
        mixed: Dict[str, float],
    ) -> float:
        """Proxy H(S_ref): spread across dimensions + internal buffer variance."""
        spreads = [
            abs(internal["v"] - external["v"]),
            abs(internal["drift"] - external["drift"]),
            abs(internal["rcs"] - external["rcs"]),
        ]
        total = sum(spreads)
        if total < 1e-9:
            dim_entropy = 0.0
        else:
            probs = [s / total for s in spreads]
            dim_entropy = -sum(p * math.log(p + 1e-12) for p in probs)

        if len(self.internal_buffer) >= 2:
            window = self.internal_buffer[-min(self.lag, len(self.internal_buffer)) :]
            arr = np.asarray([[s["v"], s["drift"], s["rcs"]] for s in window], dtype=float)
            var_entropy = float(np.mean(np.var(arr, axis=0)))
        else:
            var_entropy = 0.0

        mixed_spread = (
            abs(mixed["v"] - internal["v"])
            + abs(mixed["drift"] - internal["drift"])
            + abs(mixed["rcs"] - internal["rcs"])
        )
        return dim_entropy + var_entropy + mixed_spread * 0.1

    def _mix(self, internal: Dict[str, float], external: Dict[str, float], alpha: float) -> Dict[str, float]:
        beta = 1.0 - alpha
        return {
            "v": alpha * internal["v"] + beta * external["v"],
            "drift": alpha * internal["drift"] + beta * external["drift"],
            "rcs": alpha * internal["rcs"] + beta * external["rcs"],
        }

    def get_reference(self) -> Optional[ReferencePoint]:
        internal = self._lagged_internal()
        if internal is None:
            return None

        external = self._latest_external()
        effective_alpha = self._effective_alpha(external)
        mixed = self._mix(internal, external, effective_alpha)
        entropy = self._reference_entropy(internal, external, mixed)

        if entropy < self.entropy_floor:
            effective_alpha = self.alpha_min
            mixed = self._mix(internal, external, effective_alpha)
            entropy = self._reference_entropy(internal, external, mixed)
            source = "entropy_guard"
        elif external.get("strength", 0.0) > self.external_dominance_theta:
            source = "external_dominant"
        elif self.external_buffer:
            source = "mixed"
        else:
            source = "exogenous_default"

        lag_used = min(len(self.internal_buffer), self.lag)

        return ReferencePoint(
            v_ref=mixed["v"],
            drift_ref=mixed["drift"],
            rcs_ref=mixed["rcs"],
            external_v=external["v"],
            internal_v=internal["v"],
            alpha=effective_alpha,
            entropy=entropy,
            lag_used=lag_used,
            source=source,
        )

    def stats(self) -> Dict[str, Any]:
        ref = self.get_reference()
        return {
            "internal_len": len(self.internal_buffer),
            "external_len": len(self.external_buffer),
            "alpha": self.alpha,
            "alpha_min": self.alpha_min,
            "lag": self.lag,
            "entropy_floor": self.entropy_floor,
            "reference": ref.to_dict() if ref else None,
        }
