"""L8 — unified collapse & governance kernel types (tensor-only, observational)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

L8_CONSTRAINTS: dict[str, bool] = {
    "no_new_layer_semantics": True,
    "no_control_execution": True,
    "no_governance_activation": True,
    "no_decision_generation": True,
    "tensor_only_representation": True,
}


@dataclass
class SemanticTensor:
    dimensions: list[str]
    vector: list[float]
    representation: str = "semantic_tensor"
    projection: str = "collapsed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CollapseField:
    mode: str
    severity: float
    temporal_coherence: str
    deformation: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GovernanceSurface:
    control_surfaces: list[str]
    null_space_dim: int
    flat_graph: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SafetyEnvelope:
    versions: list[str]
    compact_signals: dict[str, Any]
    constraint_strength: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UnifiedState:
    semantic_tensor: dict[str, Any]
    collapse_field: dict[str, Any]
    governance_surface: dict[str, Any]
    safety_envelope: dict[str, Any]
    stability_index: float
    coherence_index: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class L8Report:
    unified_state: UnifiedState
    constraints: dict[str, bool] = field(default_factory=lambda: dict(L8_CONSTRAINTS))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "unified_state": self.unified_state.to_dict(),
            "constraints": self.constraints,
            "metadata": self.metadata,
        }

    def render_text(self) -> str:
        us = self.unified_state
        tensor = us.semantic_tensor
        collapse = us.collapse_field
        gov = us.governance_surface
        safety = us.safety_envelope
        lines = [
            "=== CNexus L8 — Unified Collapse & Governance Kernel ===",
            f"Representation: {tensor.get('representation', 'semantic_tensor')}",
            f"Dimensions: {', '.join(tensor.get('dimensions', []))}",
            f"Stability index: {us.stability_index:.4f}",
            f"Coherence index: {us.coherence_index:.4f}",
            f"Collapse mode: {collapse.get('mode', 'n/a')} (severity={collapse.get('severity', 0):.3f})",
            f"Governance surfaces: {len(gov.get('control_surfaces', []))} | null-space dim={gov.get('null_space_dim', 0)}",
            f"Safety envelope: v{','.join(safety.get('versions', []))} strength={safety.get('constraint_strength', 0):.3f}",
            "",
            "Structure (collapsed):",
            "  observability ──┐",
            "  L3 G0–G7 stack ─┼── semantic_tensor ── collapse_field",
            "  safety V1–V7 ───┘         │              governance_surface",
            "                            └── safety_envelope",
            "",
            "(L8: convergence layer — tensor-only, no governance activation)",
        ]
        return "\n".join(lines)

    def export_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
