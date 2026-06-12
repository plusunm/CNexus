"""Semantic Safety v5 — interpretation isolation report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.semantic_safety.v3 import build_semantic_safety_v3_report
from core.governance.semantic_safety.v5.interpretation_isolation import InterpretationIsolationLayer


@dataclass
class SemanticSafetyV5Report:
    interpretation_isolation_v5: bool = True
    isolated_reports: dict[str, dict[str, Any]] = field(default_factory=dict)
    isolation_summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    v3_on_isolated: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interpretation_isolation_v5": self.interpretation_isolation_v5,
            "isolated_reports": self.isolated_reports,
            "isolation_summaries": self.isolation_summaries,
            "v3_attack_on_isolated": self.v3_on_isolated,
            "metadata": self.metadata,
        }

    def render_text(self) -> str:
        lines = [
            "=== CNexus Semantic Safety v5 — Interpretation Isolation Report ===",
            f"Reports isolated: {len(self.isolated_reports)}",
        ]
        for label, summary in self.isolation_summaries.items():
            lines.append(
                f"  {label}: coherence={summary.get('coherence', 0):.2f}, "
                f"governance_blocked={summary.get('governance_projection_blocked')}"
            )
        score = self.v3_on_isolated.get("attack_score", {})
        lines.extend(
            [
                f"Misread risk (isolated view): {score.get('misinterpretation_risk', 0):.2f}",
                "",
                "(v5: interpretation destabilization — output readable, governance closure impossible)",
            ]
        )
        return "\n".join(lines)


class SemanticSafetyV5Reporter:
    def build(self, signals: dict[str, dict[str, Any]], *, through_v4: bool = True) -> SemanticSafetyV5Report:
        from core.governance.semantic_safety.v4 import apply_semantic_firewall

        layer = InterpretationIsolationLayer()
        isolated: dict[str, dict[str, Any]] = {}
        summaries: dict[str, dict[str, Any]] = {}

        for label, payload in signals.items():
            presentation = apply_semantic_firewall(payload) if through_v4 else payload
            result = layer.isolate(presentation)
            isolated[label] = result.output
            summaries[label] = result.isolation_status

        v3_signals = {
            label: {
                "interpretation_space": rep.get("interpretation_space", {}),
                "semantic_fragments": rep.get("semantic_fragments", []),
            }
            for label, rep in isolated.items()
        }
        v3_on_isolated = build_semantic_safety_v3_report(v3_signals, use_l3_stack=False).to_dict()

        return SemanticSafetyV5Report(
            isolated_reports=isolated,
            isolation_summaries=summaries,
            v3_on_isolated=v3_on_isolated,
            metadata={
                "interpretation_resistant_observational_os": True,
                "interpretability_instability_principle": True,
                "no_runtime_mutation": True,
                "no_governance_decision": True,
                "through_v4_firewall": through_v4,
            },
        )
