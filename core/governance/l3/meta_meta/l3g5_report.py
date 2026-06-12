"""L3-G5 — meta-meta governance boundary report."""

from __future__ import annotations

from typing import Any

from core.governance.l3.meta_meta.boundary_constructor import BoundaryConstructor
from core.governance.l3.meta_meta.layer_genesis import LayerGenesisCatalog
from core.governance.l3.meta_meta.meta_layer_engine import MetaLayerObserver
from core.governance.l3.meta_meta.ontology_drift import OntologyDriftAnalyzer
from core.governance.l3.meta_meta.types import L3G5ReportPayload


class L3G5Report:
    def __init__(self, payload: L3G5ReportPayload) -> None:
        self._payload = payload

    @property
    def layer_system_stability(self) -> float:
        return self._payload.layer_system_stability

    @property
    def meta_governance_state(self) -> str:
        return self._payload.meta_governance_state

    def to_dict(self) -> dict[str, Any]:
        return self._payload.to_dict()

    def render_text(self) -> str:
        p = self._payload
        lines = [
            "=== L3-G5 Meta-Meta Governance Boundary Report ===",
            f"Meta-governance state: {p.meta_governance_state}",
            f"Layer system stability: {p.layer_system_stability:.2f}",
            f"Boundary consistency: {p.boundary_consistency:.2f}",
            f"Ontology drift index: {p.ontology_drift_index:.2f}",
            f"Self-referential depth: {p.self_referential_depth:.0f}",
            "",
            "--- Layer Genesis Rules ---",
        ]
        for name, rule in p.layer_genesis_rules.items():
            lines.append(f"  {name}: {rule}")
        if p.integrity_violations:
            lines.extend(["", "--- Integrity Violations ---"])
            for v in p.integrity_violations:
                lines.append(f"  - {v}")
        lines.extend(
            [
                "",
                "(G5: meta_layer_definition_only — zero execution / zero layer mutation)",
            ]
        )
        return "\n".join(lines)


class L3G5Reporter:
    def build_report(self, g4_payload: dict[str, Any] | None = None) -> L3G5Report:
        genesis = LayerGenesisCatalog()
        layers = genesis.canonical_layers()
        rules = genesis.generate_layer_rules(g4_payload)
        violations = genesis.validate_layer_integrity(layers)

        constructor = BoundaryConstructor()
        boundaries = constructor.construct(layers)
        boundary_consistency = constructor.evaluate_consistency(boundaries)

        drift_analyzer = OntologyDriftAnalyzer()
        base_drift, drift_details = drift_analyzer.compute_drift(layers)
        ontology_index = (
            drift_analyzer.adjust_index_from_g4(base_drift, g4_payload or {})
            if g4_payload
            else base_drift
        )

        engine = MetaLayerObserver()
        metrics = engine.run(
            layers,
            boundaries,
            ontology_index,
            boundary_consistency=boundary_consistency,
        )
        state = engine.classify(metrics)

        payload = L3G5ReportPayload(
            layer_system_stability=metrics["layer_system_stability"],
            boundary_consistency=metrics["boundary_consistency"],
            ontology_drift_index=metrics["ontology_drift_index"],
            self_referential_depth=metrics["self_referential_depth"],
            meta_governance_state=state,
            layer_definitions=[layer.to_dict() for layer in layers],
            boundaries=[b.to_dict() for b in boundaries],
            ontology_drifts=[d.to_dict() for d in drift_details],
            layer_genesis_rules=rules,
            integrity_violations=violations,
            metadata={
                "l3_layer": "governance_boundary_g5",
                "read_only": True,
                "meta_layer_definition_only": True,
                "no_execution": True,
                "no_layer_mutation": True,
                "no_governance_activation": True,
                "meta_level_topology_awareness": True,
            },
        )
        return L3G5Report(payload)
