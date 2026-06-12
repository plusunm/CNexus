"""Semantic Safety v3 — adversarial perception attack report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.semantic_safety.v3.attack_scorer import AttackScorer
from core.governance.semantic_safety.v3.control_inference_model import ControlInferenceModel
from core.governance.semantic_safety.v3.leakage_surface_map import LeakageSurfaceMapper
from core.governance.semantic_safety.v3.mitigation_tags import derive_mitigation_tags
from core.governance.semantic_safety.v3.perception_simulator import PerceptionSimulator


@dataclass
class SemanticSafetyV3Report:
    semantic_safety_v3: bool = True
    attack_surface_map: dict[str, Any] = field(default_factory=dict)
    perception_simulation: dict[str, Any] = field(default_factory=dict)
    control_inference_chain: dict[str, Any] = field(default_factory=dict)
    attack_score: dict[str, float] = field(default_factory=dict)
    mitigation_tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_safety_v3": self.semantic_safety_v3,
            "attack_surface_map": self.attack_surface_map,
            "perception_simulation": self.perception_simulation,
            "control_inference_chain": self.control_inference_chain,
            "attack_score": self.attack_score,
            "mitigation_tags": self.mitigation_tags,
            "metadata": self.metadata,
        }

    def render_text(self) -> str:
        score = self.attack_score
        surface = self.attack_surface_map
        lines = [
            "=== CNexus Semantic Safety v3 — Attack Simulator Report ===",
            f"Attack surface: {surface.get('level', 'unknown')}",
            f"Misinterpretation risk: {score.get('misinterpretation_risk', 0):.2f}",
            f"Control reification risk: {score.get('control_reification_risk', 0):.2f}",
            f"Policy confusion risk: {score.get('policy_confusion_risk', 0):.2f}",
            f"Collapse point: {self.control_inference_chain.get('collapse_point', 'n/a')}",
            f"Mitigation tags: {', '.join(self.mitigation_tags[:5])}",
            "",
            "(v3: adversarial perception simulation — no fix / no control / no intervention)",
        ]
        return "\n".join(lines)


class SemanticSafetyV3Reporter:
    def build(self, signals: dict[str, dict[str, Any]]) -> SemanticSafetyV3Report:
        simulator = PerceptionSimulator()
        inferencer = ControlInferenceModel()
        mapper = LeakageSurfaceMapper()
        scorer = AttackScorer()

        all_misreads: list[str] = []
        all_triggered: list[str] = []
        all_nodes: list[str] = []
        max_likelihood = 0.0
        worst_collapse = "none"
        aggregate_scores = {"misinterpretation_risk": 0.0, "control_reification_risk": 0.0, "policy_confusion_risk": 0.0}
        has_any_envelope = False

        for label, payload in signals.items():
            perception = simulator.simulate(payload, path_prefix=label)
            all_misreads.extend(perception.misread_paths)
            all_triggered.extend(perception.triggered_by)

            surface = mapper.map_surface(payload, report_label=label)
            all_nodes.extend(surface.top_leak_nodes)

            has_envelope = payload.get("role") == "observational_only" and payload.get("observational_safe") is True
            has_any_envelope = has_any_envelope or has_envelope
            scores = scorer.score(perception, surface, has_envelope=has_envelope)
            for k in aggregate_scores:
                aggregate_scores[k] = max(aggregate_scores[k], scores[k])

            chain = inferencer.infer(perception)
            if chain.likelihood > max_likelihood:
                max_likelihood = chain.likelihood
                worst_collapse = chain.collapse_point

        from core.governance.semantic_safety.v3.perception_simulator import PerceptionResult

        merged_perception = PerceptionResult(
            misread_paths=sorted(set(all_misreads)),
            triggered_by=sorted(set(all_triggered)),
        )
        merged_chain = ControlInferenceModel().infer(merged_perception)
        merged_chain.likelihood = max(max_likelihood, merged_chain.likelihood)
        merged_chain.collapse_point = worst_collapse if worst_collapse != "none" else merged_chain.collapse_point

        unique_nodes = sorted(set(all_nodes))
        surface_level = (
            "high" if len(unique_nodes) >= 5 else "medium" if len(unique_nodes) >= 2 else "low" if unique_nodes else "minimal"
        )

        return SemanticSafetyV3Report(
            attack_surface_map={
                "level": surface_level,
                "high_risk_nodes": unique_nodes[:12],
                "node_count": len(unique_nodes),
            },
            perception_simulation={
                "misread_paths": merged_perception.misread_paths,
                "triggered_by": merged_perception.triggered_by[:20],
            },
            control_inference_chain=merged_chain.to_dict(),
            attack_score=aggregate_scores,
            mitigation_tags=derive_mitigation_tags(merged_perception),
            metadata={
                "adversarial_perception_simulator": True,
                "no_fix": True,
                "no_control": True,
                "no_intervention": True,
                "reports_scanned": list(signals.keys()),
                "envelope_present": has_any_envelope,
            },
        )
