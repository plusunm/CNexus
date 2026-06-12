"""L3-G1 — constraint graph + arbitration report (formal governance geometry)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.governance.l3.arbitration_engine import ArbitrationDecision
from core.governance.l3.constraint_model import ConstraintGraph
from core.governance.semantic_safety.envelope import risk_observation_label, with_observational_safety


@dataclass
class L3G1Report:
    graph_summary: dict[str, int]
    violation_score: float
    simulation_result: dict[str, Any]
    risk_observation: str
    constraint_graph: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return with_observational_safety(
            {
                "report": "L3-G1 Constraint Graph + Arbitration Report",
                "graph_summary": self.graph_summary,
                "violation_score": round(self.violation_score, 4),
                "simulation_result": self.simulation_result,
                "risk_observation": self.risk_observation,
                "constraint_graph": self.constraint_graph,
                "metadata": self.metadata,
                "semantic_note": "violation_score is a measurement — not an optimization target",
            }
        )

    def render_text(self) -> str:
        sim = self.simulation_result
        lines = [
            "=== L3-G1 Constraint Graph + Arbitration Report ===",
            f"Graph: {self.graph_summary}",
            f"Violation score: {self.violation_score:.2f}",
            f"Risk observation: {self.risk_observation}",
            "",
            "--- Simulated Arbitration (non-executing) ---",
            f"Precedence label: {sim.get('precedence_label')}",
            f"Confidence metric: {sim.get('confidence_metric')}",
            f"Reasoning: {sim.get('reasoning_narrative')}",
            "",
            "(S13–S16: simulation only — zero runtime / CDG / L1 writeback)",
        ]
        return "\n".join(lines)


class L3G1Reporter:
    def render(
        self,
        graph: ConstraintGraph,
        decision: ArbitrationDecision,
        score: float,
    ) -> L3G1Report:
        return L3G1Report(
            graph_summary=graph.summary(),
            violation_score=score,
            simulation_result=decision.to_dict(),
            risk_observation=risk_observation_label(score),
            constraint_graph=graph.to_dict(),
            metadata={
                "l3_layer": "governance_boundary_g1",
                "read_only": True,
                "simulation_only": True,
                "no_enforcement": True,
                "no_runtime_writeback": True,
                "principles": ["S13", "S14", "S15", "S16"],
            },
        )
