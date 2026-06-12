"""L3-G3 — build power field from G1 constraint graph + G2 shadow results."""

from __future__ import annotations

from typing import Any

from core.governance.l3.constraint_model import ConstraintGraph
from core.governance.l3.execution_shadow.types import ShadowState
from core.governance.l3.field_optimization.types import PowerEdge, PowerField, PowerNode


class PowerFieldBuilder:
    """Aggregate G1/G2 outputs into a unified power field (descriptive only)."""

    def build(
        self,
        g1_graph: ConstraintGraph,
        g2_shadow_results: list[ShadowState],
    ) -> PowerField:
        nodes: dict[str, PowerNode] = {}
        edges: list[PowerEdge] = []

        for node_id, node in g1_graph.nodes.items():
            weight = float(node.weight)
            nodes[node_id] = PowerNode(
                id=node_id,
                strength=weight,
                elasticity=max(0.0, min(1.0, 1.0 - weight)),
            )

        if "system_core" not in nodes:
            nodes["system_core"] = PowerNode(
                id="system_core",
                strength=0.5,
                elasticity=0.5,
            )

        for shadow in g2_shadow_results:
            cid = shadow.scenario.constraint_id
            if cid not in nodes:
                nodes[cid] = PowerNode(
                    id=cid,
                    strength=shadow.scenario.enforcement_strength,
                    elasticity=0.3,
                )
            edges.append(
                PowerEdge(
                    from_node=cid,
                    to_node="system_core",
                    tension=float(shadow.projected_impact.risk_amplification),
                )
            )

        for edge in g1_graph.edges:
            tension = float(edge.strength) * 0.5
            if edge.relation == "conflicts":
                tension *= 1.2
            edges.append(
                PowerEdge(
                    from_node=edge.from_node,
                    to_node=edge.to_node,
                    tension=tension,
                )
            )

        return PowerField(nodes=nodes, edges=edges)

    def build_from_dicts(
        self,
        g1_graph_dict: dict[str, Any],
        g2_shadow_dicts: list[dict[str, Any]],
    ) -> PowerField:
        """Rebuild from serialized G1/G2 report payloads."""
        from core.governance.l3.constraint_model import ConstraintGraph, ConstraintNode, ConstraintEdge, ConstraintType

        nodes_g1: dict[str, ConstraintNode] = {}
        for nd in g1_graph_dict.get("nodes", []):
            nodes_g1[nd["id"]] = ConstraintNode(
                id=nd["id"],
                type=ConstraintType(nd.get("type", "authority")),
                weight=float(nd.get("weight", 0.5)),
            )
        edges_g1 = [
            ConstraintEdge(
                from_node=e["from"],
                to_node=e["to"],
                relation=e.get("relation", "depends_on"),
                strength=float(e.get("strength", 0.5)),
            )
            for e in g1_graph_dict.get("edges", [])
        ]
        graph = ConstraintGraph(nodes=nodes_g1, edges=edges_g1)

        shadows: list[ShadowState] = []
        for sd in g2_shadow_dicts:
            from core.governance.l3.execution_shadow.types import ExecutionScenario, ImpactProfile

            sc = sd.get("scenario", {})
            imp = sd.get("projected_impact", {})
            shadows.append(
                ShadowState(
                    scenario=ExecutionScenario(
                        constraint_id=sc.get("constraint_id", "unknown"),
                        enforcement_strength=float(sc.get("enforcement_strength", 0.5)),
                        target_layer=sc.get("target_layer", "L2"),
                    ),
                    projected_impact=ImpactProfile(
                        stability_delta=float(imp.get("stability_delta", 0)),
                        coherence_delta=float(imp.get("coherence_delta", 0)),
                        coupling_delta=float(imp.get("coupling_delta", 0)),
                        risk_amplification=float(imp.get("risk_amplification", 0)),
                    ),
                    system_response=sd.get("system_response", ""),
                    layer_projections=sd.get("layer_projections", {}),
                )
            )
        return self.build(graph, shadows)
