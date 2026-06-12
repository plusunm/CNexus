"""Semantic Safety v6 — cognitive dissolution report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.semantic_safety.v6.cognitive_dissolution import CognitiveDissolutionLayer


@dataclass
class SemanticSafetyV6Report:
    cognitive_dissolution_v6: bool = True
    dissolved_reports: dict[str, dict[str, Any]] = field(default_factory=dict)
    dissolution_summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cognitive_dissolution_v6": self.cognitive_dissolution_v6,
            "dissolved_reports": self.dissolved_reports,
            "dissolution_summaries": self.dissolution_summaries,
            "metadata": self.metadata,
        }

    def render_text(self) -> str:
        lines = [
            "=== CNexus Semantic Safety v6 — Cognitive Dissolution Report ===",
            f"Reports dissolved: {len(self.dissolved_reports)}",
        ]
        for label, summary in self.dissolution_summaries.items():
            lines.append(
                f"  {label}: temporal={summary.get('temporal_coherence')}, "
                f"narrative_constructible={summary.get('narrative_constructible')}"
            )
        lines.extend(
            [
                "",
                "(v6: temporal + narrative collapse — continuity preconditions removed)",
            ]
        )
        return "\n".join(lines)


class SemanticSafetyV6Reporter:
    def build(self, signals: dict[str, dict[str, Any]], *, through_v5: bool = True) -> SemanticSafetyV6Report:
        from core.governance.semantic_safety.v5 import apply_interpretation_isolation

        layer = CognitiveDissolutionLayer()
        dissolved: dict[str, dict[str, Any]] = {}
        summaries: dict[str, dict[str, Any]] = {}

        for label, payload in signals.items():
            isolated = apply_interpretation_isolation(payload, through_v4=True) if through_v5 else payload
            result = layer.dissolve(isolated, source_label=label)
            dissolved[label] = result.output
            summaries[label] = result.dissolution_status

        return SemanticSafetyV6Report(
            dissolved_reports=dissolved,
            dissolution_summaries=summaries,
            metadata={
                "non_narrative_cognitive_observation_kernel": True,
                "no_runtime_mutation": True,
                "no_governance_decision": True,
                "through_v5_isolation": through_v5,
            },
        )
