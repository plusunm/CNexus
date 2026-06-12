"""Semantic Safety v4 — firewall run report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.semantic_safety.v4.semantic_firewall import SemanticFirewall
from core.governance.semantic_safety.v3 import build_semantic_safety_v3_report


@dataclass
class SemanticSafetyV4Report:
    semantic_firewall_v4: bool = True
    reports_processed: dict[str, dict[str, Any]] = field(default_factory=dict)
    firewall_summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    v3_before: dict[str, Any] = field(default_factory=dict)
    v3_after: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "semantic_firewall_v4": self.semantic_firewall_v4,
            "reports_processed": self.reports_processed,
            "firewall_summaries": self.firewall_summaries,
            "v3_attack_before": self.v3_before,
            "v3_attack_after": self.v3_after,
            "metadata": self.metadata,
        }

    def render_text(self) -> str:
        lines = [
            "=== CNexus Semantic Safety v4 — Semantic Firewall Report ===",
            f"Reports processed: {len(self.reports_processed)}",
        ]
        for label, status in self.firewall_summaries.items():
            lines.append(
                f"  {label}: projections={status.get('control_projections_removed', 0)}, "
                f"phrases={status.get('blocked_governance_phrases', 0)}"
            )
        before = self.v3_before.get("attack_score", {})
        after = self.v3_after.get("attack_score", {})
        lines.extend(
            [
                f"Misread risk before: {before.get('misinterpretation_risk', 0):.2f}",
                f"Misread risk after:  {after.get('misinterpretation_risk', 0):.2f}",
                "",
                "(v4: pre-output containment — no runtime control / no value mutation in storage)",
            ]
        )
        return "\n".join(lines)


class SemanticSafetyV4Reporter:
    def build(self, signals: dict[str, dict[str, Any]]) -> SemanticSafetyV4Report:
        firewall = SemanticFirewall()
        processed: dict[str, dict[str, Any]] = {}
        summaries: dict[str, dict[str, Any]] = {}

        for label, payload in signals.items():
            result = firewall.process(payload)
            processed[label] = result.output
            summaries[label] = result.firewall_status

        v3_before = build_semantic_safety_v3_report(signals, use_l3_stack=False).to_dict()
        after_signals = {label: payload.get("data", payload) for label, payload in processed.items()}
        v3_after = build_semantic_safety_v3_report(after_signals, use_l3_stack=False).to_dict()

        return SemanticSafetyV4Report(
            reports_processed=processed,
            firewall_summaries=summaries,
            v3_before=v3_before,
            v3_after=v3_after,
            metadata={
                "interpretation_firewall_os": True,
                "no_runtime_mutation": True,
                "no_governance_decision": True,
                "observational_payload_preserved": True,
            },
        )
