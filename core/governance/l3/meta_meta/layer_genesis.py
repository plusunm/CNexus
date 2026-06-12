"""L3-G5 — layer genesis rules (how governance layers are allowed to exist)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.meta_meta.types import LayerDefinition


class LayerGenesisCatalog:
    """Defines how governance layers are allowed to exist — descriptive only."""

    CANONICAL_RULES: dict[str, str] = {
        "L2": "interpretation_only",
        "L3-G0": "authority_detection_only",
        "L3-G1": "structural_modeling_only",
        "L3-G2": "simulation_only",
        "L3-G3": "field_optimization_shadow_only",
        "L3-G4": "reflexivity_only",
        "L3-G5": "meta_layer_definition_only",
    }

    def generate_layer_rules(self, l3_state: dict[str, Any] | None = None) -> dict[str, str]:
        rules = dict(self.CANONICAL_RULES)
        if l3_state:
            phase = l3_state.get("meta_governance_state", "")
            if phase in ("self_sealing", "drifting"):
                rules["L3-G4"] = "reflexivity_only_with_elevated_drift_observed"
        return rules

    def canonical_layers(self) -> list[LayerDefinition]:
        return [
            LayerDefinition(
                name="L2",
                purpose="Semantic interpretation over observability streams",
                allowed_operations=["interpret", "narrate", "aggregate"],
                forbidden_operations=["execute", "mutate", "enforce"],
            ),
            LayerDefinition(
                name="L3-G0",
                purpose="Authority visibility and leakage detection",
                allowed_operations=["detect", "classify", "log"],
                forbidden_operations=["execute", "mutate", "enforce"],
            ),
            LayerDefinition(
                name="L3-G1",
                purpose="Constraint graph and arbitration simulation",
                allowed_operations=["model", "simulate_arbitration"],
                forbidden_operations=["execute", "mutate", "enforce"],
            ),
            LayerDefinition(
                name="L3-G2",
                purpose="Counterfactual enforcement shadow",
                allowed_operations=["shadow_simulate", "project_impact"],
                forbidden_operations=["execute", "mutate", "enforce"],
            ),
            LayerDefinition(
                name="L3-G3",
                purpose="Power field stability optimization (non-executing)",
                allowed_operations=["optimize_shadow", "analyze_field"],
                forbidden_operations=["execute", "mutate", "enforce"],
            ),
            LayerDefinition(
                name="L3-G4",
                purpose="Meta-governance reflexivity and meta-drift observation",
                allowed_operations=["reflect", "observe_self_model"],
                forbidden_operations=["execute", "mutate", "self_modify"],
            ),
            LayerDefinition(
                name="L3-G5",
                purpose="Meta-meta layer genesis and boundary topology",
                allowed_operations=["define_layers", "evaluate_boundaries", "measure_ontology_drift"],
                forbidden_operations=["execute", "mutate", "create_layers", "collapse_boundaries"],
            ),
        ]

    def validate_layer_integrity(self, layers: list[LayerDefinition]) -> list[str]:
        violations: list[str] = []
        forbidden_global = {"execute", "mutate", "enforce", "self_modify", "create_layers"}
        for layer in layers:
            for op in layer.allowed_operations:
                if op in forbidden_global:
                    violations.append(f"{layer.name}: forbidden op in allowed_operations: {op}")
        return violations


LayerGenesisEngine = LayerGenesisCatalog  # deprecated v1 alias
