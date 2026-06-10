"""Reference deviation verifier — epistemic meta-observer (Axiom 5).

Multi-store epistemic control system contract:
- Compares observe projection to reference projection; no control authority.
- Does NOT verify Lyapunov stability on canonical state space.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.governance.cdg.invariant_reference import InvariantReferenceManifold, ReferencePoint

logger = logging.getLogger("G1.CDG.ReferenceDeviationVerifier")


@dataclass
class VerificationSnapshot:
    """Epistemic deviation snapshot — distance(observe, ref) on projected scalars."""

    stable: bool
    deviation_v: float
    deviation_drift: float
    deviation_rcs: float
    v_ref: Optional[float] = None
    drift_ref: Optional[float] = None
    rcs_ref: Optional[float] = None
    reference_entropy: Optional[float] = None
    reference_source: str = "none"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stable": self.stable,
            "deviation_v": round(self.deviation_v, 4),
            "deviation_drift": round(self.deviation_drift, 4),
            "deviation_rcs": round(self.deviation_rcs, 4),
            "v_ref": round(self.v_ref, 4) if self.v_ref is not None else None,
            "drift_ref": round(self.drift_ref, 4) if self.drift_ref is not None else None,
            "rcs_ref": round(self.rcs_ref, 4) if self.rcs_ref is not None else None,
            "reference_entropy": (
                round(self.reference_entropy, 4) if self.reference_entropy is not None else None
            ),
            "reference_source": self.reference_source,
        }


class ReferenceDeviationVerifier:
    """Relational epistemic observer: ||observe − ref|| on projected metrics."""

    def __init__(
        self,
        ref: Optional[InvariantReferenceManifold] = None,
        *,
        v_eps: float = 0.12,
        drift_eps: float = 0.08,
        rcs_eps: float = 0.15,
    ):
        self.ref = ref
        self.v_eps = v_eps
        self.drift_eps = drift_eps
        self.rcs_eps = rcs_eps

    def verify(
        self,
        state: Dict[str, Any],
        ref: Optional[ReferencePoint] = None,
    ) -> VerificationSnapshot:
        reference = ref
        if reference is None and self.ref is not None:
            reference = self.ref.get_reference()

        potential_v = float(state.get("potential_v", state.get("v", 0.0)))
        drift = float(state.get("drift", 0.0))
        rcs = float(state.get("rcs", 0.0))

        if reference is None:
            return VerificationSnapshot(
                stable=True,
                deviation_v=0.0,
                deviation_drift=0.0,
                deviation_rcs=0.0,
                reference_source="bootstrap",
            )

        deviation_v = abs(potential_v - reference.v_ref)
        deviation_drift = abs(drift - reference.drift_ref)
        deviation_rcs = abs(rcs - reference.rcs_ref)

        stable = (
            deviation_v < self.v_eps
            and deviation_drift < self.drift_eps
            and deviation_rcs < self.rcs_eps
        )

        if not stable:
            logger.warning(
                "Reference deviation: dV=%.4f dDrift=%.4f dRcs=%.4f (v_ref=%.4f, H=%.4f)",
                deviation_v,
                deviation_drift,
                deviation_rcs,
                reference.v_ref,
                reference.entropy,
            )

        return VerificationSnapshot(
            stable=stable,
            deviation_v=deviation_v,
            deviation_drift=deviation_drift,
            deviation_rcs=deviation_rcs,
            v_ref=reference.v_ref,
            drift_ref=reference.drift_ref,
            rcs_ref=reference.rcs_ref,
            reference_entropy=reference.entropy,
            reference_source=reference.source,
        )


# Backward-compatible alias (deprecated naming)
LyapunovVerifier = ReferenceDeviationVerifier
