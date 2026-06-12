"""L8 — unified kernel orchestrator."""

from __future__ import annotations

from typing import Any

from core.governance.l8.collapse_unifier import CollapseUnifier
from core.governance.l8.governance_unifier import GovernanceUnifier
from core.governance.l8.safety_unifier import SafetyUnifier
from core.governance.l8.semantic_tensor_core import SemanticTensorCore
from core.governance.l8.types import L8_CONSTRAINTS, UnifiedState


def _report_dict(report: Any) -> dict[str, Any]:
    if hasattr(report, "to_dict"):
        return report.to_dict()
    if hasattr(report, "render"):
        payload = report.render()
        return payload if isinstance(payload, dict) else {"render": payload}
    return dict(report) if isinstance(report, dict) else {"value": str(report)}


class UnifiedKernel:
    """Flatten L3 + safety stacks into a single semantic tensor field — read-only."""

    def __init__(self) -> None:
        self._tensor = SemanticTensorCore()
        self._collapse = CollapseUnifier()
        self._governance = GovernanceUnifier()
        self._safety = SafetyUnifier()

    def ingest_l3_stack(self, l3_stack: dict[str, Any]) -> dict[str, Any]:
        return {k: (v if isinstance(v, dict) else {"value": v}) for k, v in l3_stack.items()}

    def ingest_safety_stack(self, safety_stack: dict[str, Any]) -> dict[str, Any]:
        return {k: (v if isinstance(v, dict) else {"value": v}) for k, v in safety_stack.items()}

    def build_semantic_tensor(
        self,
        observability_streams: dict[str, Any],
        l3_data: dict[str, Any],
        safety_data: dict[str, Any],
    ) -> dict[str, Any]:
        gov_flat = self._governance.flatten_governance_graph(l3_data)
        safety_env = self._safety.safety_envelope_builder(safety_data)
        tensor = self._tensor.tensorize(observability_streams, gov_flat, safety_env.to_dict())
        return self._tensor.project(tensor, dimensions="collapsed")

    def project_unified_state(
        self,
        l3_stack: dict[str, Any],
        safety_stack: dict[str, Any],
        observability_streams: dict[str, Any] | None = None,
    ) -> UnifiedState:
        observability = observability_streams or {"stream_density": 0.55, "observational_only": True}
        l3_data = self.ingest_l3_stack(l3_stack)
        safety_data = self.ingest_safety_stack(safety_stack)

        tensor = self.build_semantic_tensor(observability, l3_data, safety_data)
        merged_collapse = self._collapse.merge_collapse_signals(l3_data, safety_data)
        collapse_field = self._collapse.collapse_field_solver(tensor, merged_collapse)
        governance_surface = self._governance.build_surface(l3_data)
        safety_envelope = self._safety.safety_envelope_builder(safety_data)

        return UnifiedState(
            semantic_tensor=tensor,
            collapse_field=collapse_field.to_dict(),
            governance_surface=governance_surface.to_dict(),
            safety_envelope=safety_envelope.to_dict(),
            stability_index=self._tensor.stability_score(tensor),
            coherence_index=self._tensor.compute_coherence(tensor),
        )


def build_l8_unified_state(
    l3_stack: dict[str, Any] | None = None,
    safety_stack: dict[str, Any] | None = None,
    observability_streams: dict[str, Any] | None = None,
    *,
    base_dir: str | None = None,
    use_l2_coupling: bool = False,
    auto_collect: bool = True,
) -> UnifiedState:
    if auto_collect and l3_stack is None and safety_stack is None:
        l3_stack = collect_l3_stack(base_dir=base_dir, use_l2_coupling=use_l2_coupling)
        safety_stack = collect_safety_stack()
        if observability_streams is None and base_dir:
            observability_streams = collect_observability_streams(base_dir)
    l3_stack = l3_stack or {}
    safety_stack = safety_stack or {}
    return UnifiedKernel().project_unified_state(l3_stack, safety_stack, observability_streams)


def collect_l3_stack(
    *,
    base_dir: str | None = None,
    use_l2_coupling: bool = False,
) -> dict[str, Any]:
    from core.governance.l3 import (
        build_l3_g0_report,
        build_l3_g1_report,
        build_l3_g2_report,
        build_l3_g3_report,
        build_l3_g4_report,
        build_l3_g5_report,
        build_l3_g6_report,
        build_l3_g7_report,
    )

    coupling = use_l2_coupling and base_dir is not None
    kwargs: dict[str, Any] = {
        "base_dir": base_dir if coupling else None,
        "use_l2_coupling": coupling,
    }
    return {
        "G0": _report_dict(build_l3_g0_report(**kwargs)),
        "G1": _report_dict(build_l3_g1_report(**kwargs)),
        "G2": _report_dict(build_l3_g2_report(**kwargs)),
        "G3": _report_dict(build_l3_g3_report(**kwargs)),
        "G4": _report_dict(build_l3_g4_report(**kwargs)),
        "G5": _report_dict(build_l3_g5_report(**kwargs)),
        "G6": _report_dict(build_l3_g6_report(**kwargs)),
        "G7": _report_dict(build_l3_g7_report(**kwargs)),
    }


def collect_safety_stack() -> dict[str, Any]:
    from core.governance.semantic_safety import OBSERVATIONAL_SAFETY_V2
    from core.governance.semantic_safety.v3 import build_semantic_safety_v3_report
    from core.governance.semantic_safety.v4 import build_semantic_safety_v4_report
    from core.governance.semantic_safety.v5 import build_semantic_safety_v5_report
    from core.governance.semantic_safety.v6 import build_semantic_safety_v6_report

    v3 = build_semantic_safety_v3_report().to_dict()
    v4 = build_semantic_safety_v4_report().to_dict()
    v5 = build_semantic_safety_v5_report().to_dict()
    v6_full = build_semantic_safety_v6_report().to_dict()
    v6_sample = next(iter(v6_full.get("dissolved_reports", {}).values()), v6_full)

    return {
        "v1": {"semantic_safety_v1": True, "rename_map_only": True, "observational_only": True},
        "v2": dict(OBSERVATIONAL_SAFETY_V2),
        "v3": v3,
        "v4": v4,
        "v5": v5,
        "v6": {**v6_sample, "cognitive_dissolution_v6": True},
        "v7": {
            "post_narrative_field_v7": False,
            "status": "reserved",
            "observational_only": True,
            "note": "safety v7 not implemented — L8 holds slot without layer expansion",
        },
    }


def collect_observability_streams(base_dir: str) -> dict[str, Any]:
    from pathlib import Path

    root = Path(base_dir)
    streams = ["observability/gtbs_shadow.jsonl", "observability/gtbs_transactions.jsonl"]
    present = sum(1 for s in streams if (root / s).exists())
    return {
        "base_dir": str(root),
        "stream_count": len(streams),
        "streams_present": present,
        "stream_density": round(0.4 + present * 0.25, 4),
        "observational_only": True,
    }
