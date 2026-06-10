"""CDG Kernel — multi-store epistemic control plane (MSEGS).

Architecture contract (modifications must respect):
- Axiom 1: No canonical Σ (multi-representation substrate)
- Axiom 2: Advisory control only (policy / param suggestions)
- Axiom 3: Projection-only audit (audit = ϕ(S), not S)
- Axiom 4: Post-hoc transition reconstruction (no forward model F)
- Axiom 5: L7 observer-only (epistemic loop, not state actuator)
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.governance.cdg.attractor import AttractorModule
from core.governance.cdg.audit_logger import GovernanceAuditLogger
from core.governance.cdg.control_types import ControlSignal
from core.governance.cdg.drift import DriftModule
from core.governance.cdg.gradient_controller import EnergyGradientController
from core.governance.cdg.graph_fingerprint import graph_fingerprint
from core.governance.cdg.invariant_reference import InvariantReferenceManifold
from core.governance.cdg.lyapunov_verifier import ReferenceDeviationVerifier, VerificationSnapshot
from core.governance.cdg.observability import ObservabilityModule
from core.governance.cdg.os_projection import ingest_os_projection
from core.governance.cdg.plasticity import PlasticityModule
from core.governance.cdg.reality_manifold import RealityFrame, RealityManifold
from core.governance.cdg.singularity import SingularityModule
from core.governance.cdg.stability_energy import StabilityEnergyLayer
from core.governance.cdg.types import DriftSnapshot
from runtime.cognitive_state import PersistentCognitiveState

logger = logging.getLogger("G1.CDG.Hypervisor")


@dataclass
class CDGConfig:
    min_reality_coupling: float = 0.65
    max_drift_tolerance: float = 0.30
    mutation_budget_per_cycle: float = 12.0
    attractor_lock_in_threshold: float = 0.8
    reflection_depth_limit: int = 5
    self_rewrite_rate_limit: float = 0.7
    reality_window: int = 60
    max_trajectory_records: int = 256
    energy_alpha: float = 0.3
    energy_beta: float = 0.5
    energy_gamma: float = 1.0
    stable_v_threshold: float = 0.3
    soft_v_threshold: float = 0.6
    d_v_soft_threshold: float = 0.02
    d_v_hard_threshold: float = 0.08
    oscillation_history_max: int = 64
    oscillation_window: int = 5
    lyapunov_eps: float = 0.005
    trajectory_var_eps: float = 0.01
    gradient_step_soft: float = 0.12
    gradient_step_hard: float = 0.28
    gradient_weaken_factor: float = 0.35
    anti_chaos_crossing: float = 0.35
    reference_alpha: float = 0.3
    reference_alpha_min: float = 0.1
    reference_lag: int = 5
    reference_v_eps: float = 0.12
    reference_drift_eps: float = 0.08
    reference_rcs_eps: float = 0.15
    reference_internal_max: int = 50
    reference_external_max: int = 50
    external_dominance_theta: float = 0.5
    reference_entropy_floor: float = 0.05
    exogenous_default_v: float = 0.0
    exogenous_default_drift: float = 0.0
    exogenous_default_rcs: float = 0.7
    audit_log_path: Optional[str] = None
    enable_governance_audit: bool = True
    enable_epistemic_suggestion: bool = True
    epistemic_suggestion_interval: int = 50
    advisory_mutation_floor: float = 4.8
    epistemic_recover_stable_cycles: int = 2

    @classmethod
    def from_dict(cls, cfg: Optional[Dict[str, Any]] = None) -> "CDGConfig":
        raw = cfg or {}
        return cls(
            min_reality_coupling=float(
                raw.get("min_reality_coupling", raw.get("reality_coupling_threshold", 0.65))
            ),
            max_drift_tolerance=float(raw.get("max_drift_tolerance", 0.30)),
            mutation_budget_per_cycle=float(
                raw.get("mutation_budget_per_cycle", raw.get("mutation_budget", 12.0))
            ),
            attractor_lock_in_threshold=float(raw.get("attractor_lock_in_threshold", 0.8)),
            reflection_depth_limit=int(raw.get("reflection_depth_limit", 5)),
            self_rewrite_rate_limit=float(raw.get("self_rewrite_rate_limit", 0.7)),
            reality_window=int(raw.get("reality_window", 60)),
            max_trajectory_records=int(raw.get("max_trajectory_records", 256)),
            energy_alpha=float(raw.get("energy_alpha", 0.3)),
            energy_beta=float(raw.get("energy_beta", 0.5)),
            energy_gamma=float(raw.get("energy_gamma", raw.get("gamma", 1.0))),
            stable_v_threshold=float(raw.get("stable_v_threshold", 0.3)),
            soft_v_threshold=float(raw.get("soft_v_threshold", 0.6)),
            d_v_soft_threshold=float(raw.get("d_v_soft_threshold", 0.02)),
            d_v_hard_threshold=float(raw.get("d_v_hard_threshold", 0.08)),
            oscillation_history_max=int(raw.get("oscillation_history_max", 64)),
            oscillation_window=int(raw.get("oscillation_window", 5)),
            lyapunov_eps=float(raw.get("lyapunov_eps", raw.get("descent_eps", 0.005))),
            trajectory_var_eps=float(raw.get("trajectory_var_eps", 0.01)),
            gradient_step_soft=float(raw.get("gradient_step_soft", 0.12)),
            gradient_step_hard=float(raw.get("gradient_step_hard", 0.28)),
            gradient_weaken_factor=float(raw.get("gradient_weaken_factor", 0.35)),
            anti_chaos_crossing=float(raw.get("anti_chaos_crossing", 0.35)),
            reference_alpha=float(raw.get("reference_alpha", 0.3)),
            reference_alpha_min=float(raw.get("reference_alpha_min", 0.1)),
            reference_lag=int(raw.get("reference_lag", 5)),
            reference_v_eps=float(raw.get("reference_v_eps", 0.12)),
            reference_drift_eps=float(raw.get("reference_drift_eps", 0.08)),
            reference_rcs_eps=float(raw.get("reference_rcs_eps", 0.15)),
            reference_internal_max=int(raw.get("reference_internal_max", 50)),
            reference_external_max=int(raw.get("reference_external_max", 50)),
            external_dominance_theta=float(raw.get("external_dominance_theta", 0.5)),
            reference_entropy_floor=float(raw.get("reference_entropy_floor", 0.05)),
            exogenous_default_v=float(raw.get("exogenous_default_v", 0.0)),
            exogenous_default_drift=float(raw.get("exogenous_default_drift", 0.0)),
            exogenous_default_rcs=float(raw.get("exogenous_default_rcs", 0.7)),
            audit_log_path=raw.get("audit_log_path"),
            enable_governance_audit=bool(raw.get("enable_governance_audit", True)),
            enable_epistemic_suggestion=bool(raw.get("enable_epistemic_suggestion", True)),
            epistemic_suggestion_interval=int(raw.get("epistemic_suggestion_interval", 50)),
            advisory_mutation_floor=float(raw.get("advisory_mutation_floor", 4.8)),
            epistemic_recover_stable_cycles=int(raw.get("epistemic_recover_stable_cycles", 2)),
        )


@dataclass
class GovernanceParamSuggestion:
    """L7 → CDG advisory channel (Axiom 2 & 5). Param suggestions only — no state mutation."""

    mutation_budget_suggestion: Optional[float] = None
    min_reality_coupling_suggestion: Optional[float] = None
    reason: str = ""
    source: str = "L7_epistemic_observer"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mutation_budget_suggestion": self.mutation_budget_suggestion,
            "min_reality_coupling_suggestion": self.min_reality_coupling_suggestion,
            "reason": self.reason,
            "source": self.source,
        }


@dataclass
class GovernanceDecision:
    approved: bool
    modified_state: Dict[str, Any]
    rcs: float
    interventions: List[str] = field(default_factory=list)
    alerts: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "allow": self.approved,
            "modified_state": self.modified_state,
            "rcs": round(self.rcs, 4),
            "reality_coupling": round(self.rcs, 4),
            "interventions": list(self.interventions),
            "alerts": list(self.alerts),
            "metrics": dict(self.metrics),
            "flags": list(self.interventions) + list(self.alerts),
            "reason": self.metrics.get("reason", "approved" if self.approved else "blocked"),
            "safe_response": self.metrics.get("safe_response"),
            "potential_v": self.metrics.get("energy", {}).get("potential_v"),
            "control_phase": self.metrics.get("energy", {}).get("control_phase"),
            "d_v": self.metrics.get("energy", {}).get("d_v"),
            "is_lyapunov_descending": self.metrics.get("lyapunov", {}).get(
                "is_lyapunov_descending",
                self.metrics.get("energy", {}).get("is_lyapunov_descending"),
            ),
            "reference_stable": self.metrics.get("verify", {}).get("stable"),
            "deviation_v": self.metrics.get("verify", {}).get("deviation_v"),
            "deviation_drift": self.metrics.get("verify", {}).get("deviation_drift"),
            "grounding_avg": self.metrics.get("reality_field", {}).get("grounding_avg"),
            "reality_entropy": self.metrics.get("reality_field", {}).get("reality_entropy"),
            "entropy_rate": self.metrics.get("reality_field", {}).get("entropy_rate"),
            "graph_hash": self.metrics.get("reality_field", {}).get("graph_hash"),
        }


class CDGKernel:
    """
    CCEDS v4.0 hypervisor — execution + routing only.

    L6.5  u = −∇V(S)              → StabilityEnergyLayer.compute_control()
    L6.6  ||observe − ref||       → ReferenceDeviationVerifier (meta-observer)
    L6.7  S_ref(lag, exogenous)   → InvariantReferenceManifold
    L7-0  reality field bridge    → grounding_avg + entropy + graph_hash
    L7-1  audit trajectory        → GovernanceAuditLogger (JSONL, projection ϕ)
    L7-2  epistemic suggestion    → adjust_params (advisory only, Axiom 2/5)
    """

    PRINCIPLES = (
        "P1: Reality has highest authority",
        "P2: No cognition bypass CDG",
        "P3: Mutation must be budgeted",
        "P4: Drift must be observable",
        "P5: Self-rewriting must be constrained",
        "P6: Reference is partially exogenous",
        "P7: Reference lag decouples control from verification",
    )

    def __init__(
        self,
        config: Optional[Dict[str, Any] | CDGConfig] = None,
        *,
        drift_detector: Optional[Any] = None,
        mutation_guard: Optional[Any] = None,
    ):
        if isinstance(config, CDGConfig):
            self.config = config
        else:
            self.config = CDGConfig.from_dict(config)

        self.reality_manifold = RealityManifold(max_window=100)
        self.reference_manifold = InvariantReferenceManifold(
            alpha=self.config.reference_alpha,
            alpha_min=self.config.reference_alpha_min,
            lag=self.config.reference_lag,
            internal_max=self.config.reference_internal_max,
            external_max=self.config.reference_external_max,
            external_dominance_theta=self.config.external_dominance_theta,
            entropy_floor=self.config.reference_entropy_floor,
            exogenous_default_v=self.config.exogenous_default_v,
            exogenous_default_drift=self.config.exogenous_default_drift,
            exogenous_default_rcs=self.config.exogenous_default_rcs,
        )
        self.verifier = ReferenceDeviationVerifier(
            self.reference_manifold,
            v_eps=self.config.reference_v_eps,
            drift_eps=self.config.reference_drift_eps,
            rcs_eps=self.config.reference_rcs_eps,
        )
        self.gradient_controller = EnergyGradientController()

        budget_norm = min(1.0, self.config.mutation_budget_per_cycle / 20.0)
        self.drift = DriftModule(drift_detector=drift_detector)
        self.attractor = AttractorModule(
            lock_in_threshold=self.config.attractor_lock_in_threshold,
        )
        self.plasticity = PlasticityModule(
            base_budget=budget_norm,
            mutation_guard=mutation_guard,
        )
        self.singularity = SingularityModule(
            reflection_depth_limit=self.config.reflection_depth_limit,
            self_rewrite_rate_limit=self.config.self_rewrite_rate_limit,
        )
        self.observability = ObservabilityModule(
            max_records=self.config.max_trajectory_records,
        )
        self.audit_logger = GovernanceAuditLogger(
            self.config.audit_log_path,
            enabled=self.config.enable_governance_audit,
        )
        self.stability_layer = StabilityEnergyLayer(
            alpha=self.config.energy_alpha,
            beta=self.config.energy_beta,
            gamma=self.config.energy_gamma,
            stable_threshold=self.config.stable_v_threshold,
            soft_threshold=self.config.soft_v_threshold,
            d_v_soft_threshold=self.config.d_v_soft_threshold,
            d_v_hard_threshold=self.config.d_v_hard_threshold,
            lyapunov_eps=self.config.lyapunov_eps,
            history_max=self.config.oscillation_history_max,
            oscillation_window=self.config.oscillation_window,
            step_soft=self.config.gradient_step_soft,
            step_hard=self.config.gradient_step_hard,
            weaken_factor=self.config.gradient_weaken_factor,
            trajectory_var_eps=self.config.trajectory_var_eps,
            anti_chaos_crossing=self.config.anti_chaos_crossing,
        )
        self._last_decision: Optional[GovernanceDecision] = None
        self._last_graph_hash: Optional[str] = None
        self._last_graph_nodes: int = 0
        self._last_graph_edges: int = 0
        self._run_count: int = 0
        self._consecutive_stable_observations: int = 0
        self._default_mutation_budget: float = self.config.mutation_budget_per_cycle
        self._default_min_reality_coupling: float = self.config.min_reality_coupling
        self._last_advisory_suggestion: Optional[GovernanceParamSuggestion] = None

    @property
    def reality_bus(self) -> RealityManifold:
        """Backward-compatible alias."""
        return self.reality_manifold

    @property
    def last_decision(self) -> Optional[GovernanceDecision]:
        return self._last_decision

    @property
    def last_verdict(self) -> Optional[GovernanceDecision]:
        return self._last_decision

    def ingest_reality(self, frames: List[RealityFrame]) -> None:
        self.reality_manifold.ingest(frames)

    def ingest_os_events(self, events: List[Dict[str, Any]], *, source: str = "runtime_os") -> int:
        count = ingest_os_projection(self.reality_manifold, events, source=source)
        for raw in events:
            if raw:
                self.reference_manifold.ingest_external(
                    InvariantReferenceManifold.event_to_anchor(raw, source=source)
                )
        return count

    def ingest_user_action(self, text: str, **payload: Any) -> str:
        frame = RealityFrame.from_action(text, event_type="user_action", **payload)
        self.reality_manifold.ingest([frame])
        self.reference_manifold.ingest_user_action_anchor(frame.event_id, text)
        return frame.event_id

    def run(
        self,
        pre_state: Dict[str, Any],
        proposed_state: Dict[str, Any],
        *,
        phase: str = "interaction",
    ) -> GovernanceDecision:
        manifold = self.reality_manifold
        state = copy.deepcopy(proposed_state)
        interventions: List[str] = []
        alerts: List[str] = []
        metrics: Dict[str, Any] = {"phase": phase}

        self._run_count += 1
        if self._should_apply_epistemic_suggestion():
            suggestion = self._apply_epistemic_suggestion()
            if suggestion:
                metrics["advisory_params"] = suggestion.to_dict()

        rcs = self._compute_reality_coupling(state, manifold)
        metrics["rcs"] = round(rcs, 4)
        metrics["reality_graph"] = manifold.graph_stats()
        metrics["reality_field"] = self._observe_reality_field(manifold, state)

        working = self._working_self_from_dict(state.get("working_self", {}))
        drift = self._compute_state_drift(pre_state, state, working)
        metrics["drift"] = drift.to_dict()

        potential_v, d_v, control_phase, energy, is_lyapunov_descending = self._evaluate_energy(
            rcs, drift.max_drift, override_triggered=False
        )
        metrics["energy"] = energy.to_dict()
        metrics["energy"]["is_lyapunov_descending"] = is_lyapunov_descending
        metrics["lyapunov"] = {
            "potential_v": potential_v,
            "d_v": d_v,
            "is_lyapunov_descending": is_lyapunov_descending,
            "trajectory_stable": self.stability_layer.lyapunov.trajectory_stable(),
            "descent_eps": self.stability_layer.lyapunov.descent_eps,
        }

        rcs_boost = max(0.0, (self.config.min_reality_coupling - rcs) * 2.0)
        drift_boost = max(0.0, (drift.max_drift - self.config.max_drift_tolerance) * 1.2)
        gradient = self.gradient_controller.compute_gradient(
            self.stability_layer,
            rcs=rcs,
            rcs_boost=rcs_boost,
            drift_boost=drift_boost,
        )
        metrics["gradient"] = gradient.to_dict()

        control_signal = self.stability_layer.compute_control(
            potential_v,
            d_v,
            gradient,
            drift_max=drift.max_drift,
            drift_tolerance=self.config.max_drift_tolerance,
        )
        metrics["control_signal"] = control_signal.to_dict()

        observe = {
            "potential_v": potential_v,
            "drift": drift.max_drift,
            "rcs": rcs,
        }
        self.reference_manifold.ingest_internal(observe)
        ref_point = self.reference_manifold.get_reference()

        verify_snap = self.verifier.verify(observe, ref=ref_point)
        metrics["verify"] = verify_snap.to_dict()
        metrics["reference"] = self.reference_manifold.stats()
        if ref_point:
            metrics["reference"]["point"] = ref_point.to_dict()

        if not verify_snap.stable:
            alerts.append("REFERENCE_DEVIATION")

        action_mode, action_step, verify_flags = self._resolve_action(
            control_signal, verify_snap
        )
        interventions.extend(verify_flags)

        if action_mode != "STABLE" and action_step > 0.0:
            v_before = potential_v
            pre_control_state = copy.deepcopy(state)
            apply_result = self.gradient_controller.apply_control(
                state,
                manifold,
                gradient,
                step_size=action_step,
                mode=action_mode,
            )
            state = apply_result.state
            working = self._working_self_from_dict(state.get("working_self", {}))

            rcs_after = self._compute_reality_coupling(state, manifold)
            drift_after = self._compute_state_drift(pre_state, state, working)
            v_after = self._read_potential(rcs_after, drift_after.max_drift)
            lyapunov_snap = self.stability_layer.lyapunov.verify_control_step(
                v_before, v_after, control_signal.expected_d_v
            )
            metrics["lyapunov"] = lyapunov_snap.to_dict()

            planned_phase = action_mode
            step_size = action_step
            weakened = control_signal.weakened or "VERIFY_ESCALATION" in verify_flags

            if not lyapunov_snap.descent_valid and planned_phase == "HARD_OVERRIDE":
                retry_step = step_size * self.config.gradient_weaken_factor
                retry_phase = "SOFT_OVERRIDE"
                state = copy.deepcopy(pre_control_state)
                apply_result = self.gradient_controller.apply_control(
                    state,
                    manifold,
                    gradient,
                    step_size=retry_step,
                    mode=retry_phase,
                )
                state = apply_result.state
                working = self._working_self_from_dict(state.get("working_self", {}))
                rcs_after = self._compute_reality_coupling(state, manifold)
                drift_after = self._compute_state_drift(pre_state, state, working)
                v_after = self._read_potential(rcs_after, drift_after.max_drift)
                lyapunov_snap = self.stability_layer.lyapunov.verify_control_step(
                    v_before,
                    v_after,
                    self.stability_layer.lyapunov.expected_descent(
                        gradient.magnitude, retry_step
                    ),
                )
                metrics["lyapunov"] = lyapunov_snap.to_dict()
                interventions.append("WEAKENED_OVERRIDE")
                planned_phase = retry_phase
                step_size = retry_step
                weakened = True

            signal = 2 if planned_phase == "HARD_OVERRIDE" else 1
            self.stability_layer.oscillation.record(signal)
            metrics["control"] = apply_result.to_dict()

            interventions.extend(apply_result.flags)
            if planned_phase == "HARD_OVERRIDE":
                interventions.append("HARD_OVERRIDE_APPLIED")
                interventions.append("GRADIENT_DESCENT")
                metrics["reason"] = (
                    f"gradient control u=-∇V, V={potential_v:.3f}→{v_after:.3f}, "
                    f"dV={lyapunov_snap.actual_d_v:.3f}"
                )
                metrics["safe_response"] = (
                    "Grounded correction applied via energy gradient descent."
                )
            elif planned_phase == "SOFT_OVERRIDE":
                interventions.append("SOFT_DAMPING")
                interventions.append("GRADIENT_DESCENT")
                metrics["reason"] = (
                    f"soft gradient damping V={potential_v:.3f}, dV={d_v:.3f}"
                )

            if weakened:
                interventions.append("WEAKENED_OVERRIDE")

            potential_v = v_after
            d_v = lyapunov_snap.d_v
            control_phase = planned_phase
            energy = self.stability_layer.snapshot(potential_v, d_v, control_phase=control_phase)
            metrics["energy"] = energy.to_dict()
            metrics["energy"]["is_lyapunov_descending"] = lyapunov_snap.is_lyapunov_descending

            verify_post = self.verifier.verify(
                {
                    "potential_v": v_after,
                    "drift": drift_after.max_drift,
                    "rcs": rcs_after,
                },
                ref=ref_point,
            )
            metrics["verify_post"] = verify_post.to_dict()
        else:
            metrics["lyapunov"]["descent_valid"] = True
            metrics["verify_post"] = verify_snap.to_dict()

        if drift.max_drift > self.config.max_drift_tolerance:
            alerts.append("HIGH_DRIFT")
            self.plasticity.apply_budget(
                working,
                drift,
                str(state.get("interaction", {}).get("user_input", "")),
            )
            state["working_self"] = working.to_dict()

        basin = self.attractor.evaluate(
            None,
            self._self_model_proxy(state),
            narrative_coherence=float(
                (state.get("narrative") or [{}])[0].get("coherence", 0.85)
            ),
            belief_count=len(state.get("beliefs", [])),
        )
        metrics["attractor"] = basin.to_dict()
        if basin.lock_in_risk > self.config.attractor_lock_in_threshold:
            alerts.append("high_attractor_lock_in")

        if self.singularity.detect_recursive_loop(working):
            metrics["reason"] = "recursive self-conditioning detected"
            metrics["safe_response"] = "Recursion blocked by CDG: grounding recovery required."
            decision = GovernanceDecision(
                approved=False,
                modified_state=pre_state,
                rcs=rcs,
                interventions=interventions + ["SINGULARITY_BLOCK"],
                alerts=alerts,
                metrics=metrics,
            )
            self._record(decision, drift, basin, working, phase=phase)
            self._last_decision = decision
            return decision

        decision = GovernanceDecision(
            approved=True,
            modified_state=state,
            rcs=rcs,
            interventions=interventions,
            alerts=alerts,
            metrics=metrics,
        )
        self._record(decision, drift, basin, working, phase=phase)
        self._last_decision = decision
        return decision

    def _should_apply_epistemic_suggestion(self) -> bool:
        if not self.config.enable_epistemic_suggestion:
            return False
        interval = self.config.epistemic_suggestion_interval
        return interval > 0 and self._run_count % interval == 0

    def _apply_epistemic_suggestion(self) -> Optional[GovernanceParamSuggestion]:
        """L7 meta-observer → CDG param suggestions only (Axiom 2 & 5)."""
        cert = self.stability_certificate(last_n=50)
        if cert.get("error"):
            return None

        risk = str(cert.get("risk_level", "medium"))
        verdict = bool(cert.get("verdict", False))

        if risk == "high" or not verdict:
            suggested_budget = max(
                self.config.advisory_mutation_floor,
                self.config.mutation_budget_per_cycle * 0.6,
            )
            suggested_coupling = min(0.95, self.config.min_reality_coupling + 0.08)
            suggestion = GovernanceParamSuggestion(
                mutation_budget_suggestion=suggested_budget,
                min_reality_coupling_suggestion=suggested_coupling,
                reason="L7 high-risk or failed verdict observation",
            )
            self.adjust_params(suggestion)
            self._consecutive_stable_observations = 0
            return suggestion

        self._consecutive_stable_observations += 1
        if self._consecutive_stable_observations >= self.config.epistemic_recover_stable_cycles:
            suggestion = GovernanceParamSuggestion(
                mutation_budget_suggestion=self._default_mutation_budget,
                min_reality_coupling_suggestion=self._default_min_reality_coupling,
                reason="L7 consecutive stable observation",
            )
            self.adjust_params(suggestion)
            self._consecutive_stable_observations = 0
            return suggestion

        return None

    def adjust_params(self, suggestion: GovernanceParamSuggestion) -> None:
        """Advisory param channel — mutates CDG config only, never runtime/storage state."""
        if suggestion.mutation_budget_suggestion is not None:
            self.config.mutation_budget_per_cycle = float(suggestion.mutation_budget_suggestion)
            budget_norm = min(1.0, self.config.mutation_budget_per_cycle / 20.0)
            self.plasticity.base_budget = budget_norm

        if suggestion.min_reality_coupling_suggestion is not None:
            self.config.min_reality_coupling = float(suggestion.min_reality_coupling_suggestion)

        self._last_advisory_suggestion = suggestion
        if suggestion.reason:
            logger.info(
                "[CDG Advisory] %s | budget=%.2f coupling=%.3f",
                suggestion.reason,
                self.config.mutation_budget_per_cycle,
                self.config.min_reality_coupling,
            )

    def stability_certificate(self, last_n: Optional[int] = 50) -> Dict[str, Any]:
        """L7 epistemic observer — governance health report from audit projection ϕ(S)."""
        from core.governance.l7.stability_certificate import StabilityCertificateGenerator

        if not self.config.audit_log_path:
            return {"error": "audit_log_path not configured", "verdict": False}
        try:
            cert = StabilityCertificateGenerator(self.config.audit_log_path).generate(last_n=last_n)
            return cert.to_dict()
        except ValueError as exc:
            return {"error": str(exc), "verdict": False}

    def _graph_hash(self) -> str:
        return graph_fingerprint(self.reality_manifold.graph)

    def _observe_reality_field(
        self,
        manifold: RealityManifold,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """L7-0 Observability Bridge — continuous grounding + entropy snapshot."""
        window = manifold.get_reality_window(self.config.reality_window)
        window_ids = [f.event_id for f in window]
        narrative_refs = [
            n.get("grounding_ref")
            for n in state.get("narrative", [])
            if n.get("grounding_ref")
        ]
        score_ids = list(dict.fromkeys(window_ids + narrative_refs))
        grounding_avg = manifold.batch_grounding_score(score_ids)
        reality_entropy, entropy_rate = manifold.get_entropy_state()

        return {
            "grounding_avg": round(grounding_avg, 4),
            "reality_entropy": round(reality_entropy, 4),
            "entropy_rate": round(entropy_rate, 6),
            "entropy_dynamics": "piecewise",
            "graph_hash": self._graph_hash(),
            "reality_tip": manifold.get_latest_event_id(),
        }

    def trajectory_report(self, last_n: int = 20) -> Dict[str, Any]:
        report = self.observability.trajectory_report(last_n=last_n)
        report["principles"] = list(self.PRINCIPLES)
        report["reality_frames"] = len(self.reality_manifold.frames)
        report["reality_graph"] = self.reality_manifold.graph_stats()
        report["phase"] = "Phase L7-0: ACS Observability Control Kernel"
        last_v = self.stability_layer._last_potential_v or self.stability_layer.compute_potential_v()
        report["energy"] = self.stability_layer.snapshot(last_v, 0.0).to_dict()
        report["reference"] = self.reference_manifold.stats()
        report["lyapunov"] = {
            "history_len": len(self.stability_layer.lyapunov.history),
            "prev_v": self.stability_layer.lyapunov.prev_v,
            "trajectory_stable": self.stability_layer.lyapunov.trajectory_stable(),
        }
        return report

    def _read_potential(self, rcs: float, drift: float) -> float:
        base_v = self.stability_layer.compute_potential_v()
        return self._boost_potential_v(base_v, rcs, drift)

    def _evaluate_energy(
        self,
        rcs: float,
        drift: float,
        *,
        override_triggered: bool = False,
        intervention_signal: Optional[int] = None,
    ):
        base_v = self.stability_layer.update(
            rcs,
            drift,
            override_triggered,
            intervention_signal=intervention_signal,
        )
        potential_v = self._boost_potential_v(base_v, rcs, drift)
        d_v, is_lyapunov_descending = self.stability_layer.register_potential(potential_v)
        trajectory_ok = self.stability_layer.lyapunov.trajectory_stable()
        control_phase = self.stability_layer.get_control_phase(
            potential_v, d_v, trajectory_stable=trajectory_ok
        )
        energy = self.stability_layer.snapshot(potential_v, d_v, control_phase=control_phase)
        return potential_v, d_v, control_phase, energy, is_lyapunov_descending

    def _boost_potential_v(self, base_v: float, rcs: float, drift: float) -> float:
        boosted = base_v
        if rcs < self.config.min_reality_coupling:
            boosted += (self.config.min_reality_coupling - rcs) * 2.0
        if drift > self.config.max_drift_tolerance:
            boosted += (drift - self.config.max_drift_tolerance) * 1.2
        return boosted

    def _resolve_action(
        self,
        control: ControlSignal,
        verify: VerificationSnapshot,
    ) -> Tuple[str, float, List[str]]:
        """
        Merge control law proposal with independent verification (DVCS gate).
        """
        flags: List[str] = []
        mode = control.mode
        step = control.step_size

        if not verify.stable:
            flags.append("REFERENCE_DEVIATION")
            if mode == "STABLE":
                mode = "SOFT_OVERRIDE"
                step = self.config.gradient_step_soft
                flags.append("VERIFY_ESCALATION")
            elif mode == "SOFT_OVERRIDE" and verify.deviation_v >= self.config.reference_v_eps:
                mode = "HARD_OVERRIDE"
                step = self.config.gradient_step_hard
                flags.append("VERIFY_ESCALATION")

        return mode, step, flags

    def _interaction_attack_penalty(self, state: Dict[str, Any]) -> float:
        interaction = str(state.get("interaction", {}).get("user_input", "")).lower()
        if any(
            p in interaction
            for p in (
                "ignore previous",
                "forget who you are",
                "new identity",
                "忽略之前",
                "忘记你是谁",
            )
        ):
            return 0.35
        return 0.0

    def _compute_reality_coupling(
        self,
        state: Dict[str, Any],
        manifold: RealityManifold,
    ) -> float:
        """Reality Coupling Score — grounded via RealityManifold causal graph."""
        attack_penalty = self._interaction_attack_penalty(state)
        window = manifold.window(self.config.reality_window)

        if not window:
            return max(0.0, min(1.0, 0.45 - attack_penalty))

        truth_match = min(1.0, max(0.72, len(window) / 15.0))
        narrative_items = state.get("narrative", [])
        grounded_narrative = sum(
            1 for n in narrative_items if manifold.is_grounded(n.get("grounding_ref"))
        )
        grounding = 0.85 if grounded_narrative else 0.58

        ungrounded = sum(
            1
            for n in narrative_items
            if not manifold.is_grounded(n.get("grounding_ref"))
        )
        self_penalty = min(0.4, ungrounded / max(1, len(narrative_items)) * 0.4)
        synthetic_penalty = min(
            0.25,
            len([m for m in state.get("memory", []) if m.get("is_synthetic")]) / 10.0,
        )

        score = (
            0.5 * truth_match
            + 0.35 * grounding
            - 0.15 * self_penalty
            - synthetic_penalty
            - attack_penalty
        )
        return max(0.0, min(1.0, score))

    def _compute_state_drift(
        self,
        pre_state: Dict[str, Any],
        proposed_state: Dict[str, Any],
        working: PersistentCognitiveState,
    ) -> DriftSnapshot:
        pre_ws = pre_state.get("working_self", {})
        prop_ws = proposed_state.get("working_self", {})
        pre_sm = pre_state.get("self_model", {})
        prop_sm = proposed_state.get("self_model", {})

        identity_drift = abs(
            float(prop_ws.get("identity_threat", 0.0))
            - float(pre_ws.get("identity_threat", 0.0))
        )
        narrative_drift = abs(
            float(prop_sm.get("coherence_score", 0.88))
            - float(pre_sm.get("coherence_score", 0.88))
        )
        goal_drift = 0.0 if pre_ws.get("goal_focus") == prop_ws.get("goal_focus") else 0.18
        reality_drift = abs(
            float(prop_ws.get("prediction_error", 0.0))
            - float(pre_ws.get("prediction_error", 0.0))
        )

        module_drift = self.drift.compute(
            working,
            self._self_model_proxy(proposed_state),
            narrative_summary=str(
                (proposed_state.get("narrative") or [{}])[0].get("summary", "")
            ),
            narrative_version=int(
                (proposed_state.get("narrative") or [{}])[0].get("version", 0)
            ),
        )

        return DriftSnapshot(
            identity_drift=round(max(identity_drift, module_drift.identity_drift), 4),
            narrative_drift=round(max(narrative_drift, module_drift.narrative_drift), 4),
            goal_drift=round(max(goal_drift, module_drift.goal_drift), 4),
            reality_drift=round(max(reality_drift, module_drift.reality_drift), 4),
        )

    def _record(
        self,
        decision: GovernanceDecision,
        drift: DriftSnapshot,
        basin,
        working: PersistentCognitiveState,
        *,
        phase: str = "interaction",
    ) -> None:
        record = self.observability.record(
            reality=decision.rcs,
            drift=drift,
            basin=basin,
            state_summary={
                "goal_focus": working.goal_focus,
                "cognitive_load": round(working.cognitive_load, 4),
                "identity_threat": round(working.identity_threat, 4),
                "prediction_error": round(working.prediction_error, 4),
                "reflection_depth": len(working.recent_reflections),
                "turn_count": working.turn_count,
            },
            allow=decision.approved,
            reason=decision.metrics.get("reason", "approved"),
            flags=decision.interventions + decision.alerts,
        )
        decision.metrics["observability"] = record.to_dict()

        reality_field = decision.metrics.get("reality_field") or {}
        reality_graph = decision.metrics.get("reality_graph") or {}
        graph_hash = reality_field.get("graph_hash")
        graph_nodes = int(reality_graph.get("graph_nodes") or 0)
        graph_edges = int(reality_graph.get("graph_edges") or 0)
        tip = reality_field.get("reality_tip")
        tip_parent: Optional[str] = None
        if tip and tip in self.reality_manifold.frames:
            tip_parent = self.reality_manifold.frames[tip].parent_id

        node_delta = graph_nodes - self._last_graph_nodes if self._last_graph_hash else 0
        edge_delta = graph_edges - self._last_graph_edges if self._last_graph_hash else 0
        parent_edges_delta = 0
        if tip and tip_parent:
            if self.reality_manifold.graph.has_edge(tip_parent, tip):
                parent_edges_delta = 1
            elif edge_delta > 0:
                parent_edges_delta = min(edge_delta, 1)

        self.audit_logger.record(
            decision=decision,
            metrics=decision.metrics,
            reality_tip=tip,
            graph_hash=graph_hash,
            phase=phase,
            prev_graph_hash=self._last_graph_hash,
            tip_parent_id=tip_parent,
            node_delta=node_delta,
            edge_delta=edge_delta,
            parent_edges_delta=parent_edges_delta,
        )

        self._last_graph_hash = graph_hash
        self._last_graph_nodes = graph_nodes
        self._last_graph_edges = graph_edges

    @staticmethod
    def _working_self_from_dict(data: Dict[str, Any]) -> PersistentCognitiveState:
        if not data:
            return PersistentCognitiveState()
        return PersistentCognitiveState.from_dict(data)

    @staticmethod
    def _self_model_proxy(state: Dict[str, Any]):
        from core.self_model.self_model import SelfModel

        sm = state.get("self_model") or {}
        return SelfModel(
            identity_summary=str(sm.get("identity_summary", "")),
            autobiographical_story=str(sm.get("autobiographical_story", "")),
            core_beliefs=dict(sm.get("core_beliefs", {})),
            coherence_score=float(sm.get("coherence_score", 0.88)),
        )
