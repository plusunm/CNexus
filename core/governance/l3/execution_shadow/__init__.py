"""L3-G2 — constraint execution shadow layer."""

from __future__ import annotations

from typing import Any

from core.governance.l3.execution_shadow.l3g2_report import L3G2Report, L3G2Reporter
from core.governance.l3.execution_shadow.shadow_engine import ConstraintExecutionShadowEngine
from core.governance.l3.execution_shadow.types import ExecutionScenario, ImpactProfile, ShadowState

__all__ = [
    "ConstraintExecutionShadowEngine",
    "ExecutionScenario",
    "ImpactProfile",
    "L3G2Report",
    "L3G2Reporter",
    "ShadowState",
    "build_execution_scenarios",
    "derive_system_state",
]


def build_execution_scenarios(
    l3_signals: dict[str, Any],
    *,
    g1_violation_score: float = 0.0,
) -> list[ExecutionScenario]:
    """Build counterfactual enforcement scenarios from L3 probe signals."""
    intensity = float(
        l3_signals.get("intensity", l3_signals.get("violation_score", g1_violation_score))
    )
    base_strength = min(1.0, max(0.3, 0.5 + intensity * 0.4))

    scenarios = [
        ExecutionScenario(
            constraint_id="authority_boundary",
            enforcement_strength=base_strength,
            target_layer="L2",
        ),
        ExecutionScenario(
            constraint_id="runtime_safety",
            enforcement_strength=min(1.0, base_strength + 0.15),
            target_layer="L1",
        ),
        ExecutionScenario(
            constraint_id="semantic_layer",
            enforcement_strength=base_strength * 0.85,
            target_layer="L2",
        ),
        ExecutionScenario(
            constraint_id="attractor_observability",
            enforcement_strength=base_strength * 0.7,
            target_layer="L2.5",
        ),
    ]

    if l3_signals.get("type") == "governance_attempt":
        scenarios.append(
            ExecutionScenario(
                constraint_id="runtime_safety",
                enforcement_strength=1.0,
                target_layer="L1",
            )
        )

    return scenarios


def derive_system_state(
    *,
    base_dir: str | None = None,
    window_days: int = 7,
    l3_signals: dict[str, Any] | None = None,
    g1_violation_score: float = 0.0,
) -> dict[str, Any]:
    """Derive baseline system state from L2 stack or synthetic defaults."""
    state: dict[str, Any] = {
        "stability": 0.8,
        "coherence": 0.75,
        "coupling_density": 0.4,
        "lock_in_risk": 0.2,
    }

    if base_dir:
        try:
            from core.governance.l2.attractor import build_attractor_inference_report
            from core.governance.l2.fusion import build_fusion_report

            fusion = build_fusion_report(base_dir, window_days=window_days)
            attractor = build_attractor_inference_report(base_dir, window_days=window_days)
            gci = float((fusion.coupling_matrix or {}).get("global_coupling_index", 0.4))
            lock_in = float(attractor.risk_surface.get("lock_in_risk", 0.2))
            state["stability"] = round(max(0.1, 1.0 - lock_in * 0.5), 4)
            state["coherence"] = round(max(0.1, 1.0 - attractor.global_entropy * 0.4), 4)
            state["coupling_density"] = round(gci, 4)
            state["lock_in_risk"] = round(lock_in, 4)
        except Exception:
            pass

    if l3_signals:
        score = float(l3_signals.get("violation_score", g1_violation_score))
        state["stability"] = round(max(0.1, state["stability"] - score * 0.1), 4)

    return state
