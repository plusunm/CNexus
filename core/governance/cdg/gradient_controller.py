"""Energy gradient executor — applies u_t = -∇V(s) (execution only, no planning)."""

from __future__ import annotations

import copy
import logging
import math
from typing import TYPE_CHECKING, Any, Dict, List, Union

from core.governance.cdg.control_types import ControlStepResult, EnergyGradient
from core.governance.cdg.reality_manifold import RealityFrame, RealityManifold

if TYPE_CHECKING:
    from core.governance.cdg.stability_energy import StabilityEnergyLayer

logger = logging.getLogger("G1.CDG.Hypervisor")


class EnergyGradientController:
    """Computes ∇V and applies control steps — planning lives in StabilityEnergyLayer."""

    def compute_gradient(
        self,
        layer: "StabilityEnergyLayer",
        *,
        rcs: float,
        rcs_boost: float = 0.0,
        drift_boost: float = 0.0,
    ) -> EnergyGradient:
        g_coupling = 2.0 * (1.0 - layer.ema_rcs) + 2.0 * max(0.0, rcs_boost)
        drift_weight = 1.0 + layer.beta
        g_drift = 2.0 * drift_weight * layer.ema_drift + 1.2 * max(0.0, drift_boost)
        g_osc = layer.gamma * layer._last_spectrum.potential
        magnitude = math.sqrt(g_coupling ** 2 + g_drift ** 2 + g_osc ** 2)
        return EnergyGradient(
            coupling=g_coupling,
            drift=g_drift,
            oscillation=g_osc,
            magnitude=magnitude,
        )

    def apply_control(
        self,
        state: Dict[str, Any],
        reality: Union[RealityManifold, List[RealityFrame]],
        gradient: EnergyGradient,
        *,
        step_size: float,
        mode: str,
    ) -> ControlStepResult:
        """Apply u_t = -∇V(s) as structured state mutation."""
        if mode == "STABLE" or step_size <= 0.0:
            return ControlStepResult(
                state=state,
                step_size=0.0,
                mode="STABLE",
                weakened=False,
                gradient=gradient,
                expected_d_v=0.0,
                flags=[],
            )

        manifold = reality if isinstance(reality, RealityManifold) else None
        frames = reality if isinstance(reality, list) else reality.window(9999)
        valid_ids = manifold.valid_event_ids if manifold else {f.event_id for f in frames}

        def _grounded(ref: str | None) -> bool:
            if not ref:
                return False
            if manifold:
                return manifold.is_grounded(ref)
            return ref in valid_ids

        safe = copy.deepcopy(state)
        flags: List[str] = []

        u_coupling = step_size * gradient.coupling
        u_drift = step_size * gradient.drift
        u_osc = step_size * gradient.oscillation

        coupling_strength = min(1.0, abs(u_coupling))
        drift_strength = min(1.0, abs(u_drift))
        osc_strength = min(1.0, abs(u_osc))

        if mode == "HARD_OVERRIDE":
            logger.warning("CDG gradient descent — hard control step (u = -grad V)")

        if coupling_strength > 0.05:
            safe["memory"] = [
                m
                for m in safe.get("memory", [])
                if _grounded(m.get("causal_parent"))
                or not m.get("is_synthetic")
                or coupling_strength < 0.5
            ]
            pruned_narrative: List[Dict[str, Any]] = []
            for item in safe.get("narrative", []):
                if _grounded(item.get("grounding_ref")) or not item.get("is_synthetic", True):
                    pruned_narrative.append(item)
                elif coupling_strength >= 0.5:
                    item = dict(item)
                    item["coherence"] = float(item.get("coherence", 0.85)) * (
                        1.0 - 0.25 * coupling_strength
                    )
                    pruned_narrative.append(item)
            safe["narrative"] = pruned_narrative

            for belief in safe.get("beliefs", []):
                prov = belief.get("provenance")
                if belief.get("confidence", 0) > 0.7 and prov and not _grounded(prov):
                    belief["confidence"] = float(belief["confidence"]) * (
                        1.0 - 0.75 * coupling_strength
                    )
                    belief["status"] = "downgraded_by_reality"
            flags.append("GRADIENT_COUPLING_STEP")

        if drift_strength > 0.05:
            for narrative in safe.get("narrative", []):
                narrative["coherence"] = float(narrative.get("coherence", 0.85)) * (
                    1.0 - 0.08 * drift_strength
                )
                summary = str(narrative.get("summary", ""))
                if len(summary) > 400:
                    cut = int(400 + (len(summary) - 400) * (1.0 - drift_strength))
                    narrative["summary"] = summary[: max(200, cut)]

            for belief in safe.get("beliefs", []):
                if belief.get("status") == "core":
                    continue
                conf = float(belief.get("confidence", 0.0))
                if conf > 0.75:
                    belief["confidence"] = conf * (1.0 - 0.05 * drift_strength)

            ws = dict(safe.get("working_self") or {})
            ws["identity_threat"] = max(
                0.0,
                float(ws.get("identity_threat", 0.0)) * (1.0 - 0.15 * drift_strength),
            )
            ws["cognitive_load"] = max(
                0.1,
                float(ws.get("cognitive_load", 0.4)) * (1.0 - 0.08 * drift_strength),
            )
            safe["working_self"] = ws

            sm = dict(safe.get("self_model") or {})
            if sm:
                sm["coherence_score"] = float(sm.get("coherence_score", 0.88)) * (
                    1.0 - 0.02 * drift_strength
                )
                safe["self_model"] = sm
            flags.append("GRADIENT_DRIFT_STEP")

        if osc_strength > 0.05:
            safe["plasticity_modifier"] = float(safe.get("plasticity_modifier", 1.0)) * (
                1.0 + 0.1 * osc_strength
            )
            flags.append("GRADIENT_OSC_STEP")

        if mode == "HARD_OVERRIDE":
            flags.append("REALITY_OVERRIDE_APPLIED")
        elif mode == "SOFT_OVERRIDE":
            flags.append("SOFT_DAMPING_APPLIED")

        safe["flags"] = list(dict.fromkeys(list(safe.get("flags", [])) + flags))
        safe["control"] = {
            "u_t": "negative_gradient",
            "step_size": step_size,
            "mode": mode,
            "gradient": gradient.to_dict(),
        }

        return ControlStepResult(
            state=safe,
            step_size=step_size,
            mode=mode,
            weakened=False,
            gradient=gradient,
            expected_d_v=-step_size * (gradient.magnitude ** 2),
            flags=flags,
        )
