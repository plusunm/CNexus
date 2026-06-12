"""L8 — unified report builder."""

from __future__ import annotations

from typing import Any

from core.governance.l8.types import L8Report, L8_CONSTRAINTS, UnifiedState


class L8Reporter:
    def build(self, unified_state: UnifiedState, *, metadata: dict[str, Any] | None = None) -> L8Report:
        meta = {
            "kernel": "unified_collapse_governance",
            "observational_only": True,
            "no_runtime_effect": True,
            "convergence_not_expansion": True,
        }
        if metadata:
            meta.update(metadata)
        return L8Report(
            unified_state=unified_state,
            constraints=dict(L8_CONSTRAINTS),
            metadata=meta,
        )


def build_l8_report(
    l3_stack: dict[str, Any] | None = None,
    safety_stack: dict[str, Any] | None = None,
    observability_streams: dict[str, Any] | None = None,
    *,
    base_dir: str | None = None,
    use_l2_coupling: bool = False,
    auto_collect: bool = True,
) -> L8Report:
    from core.governance.l8.unified_kernel import build_l8_unified_state

    state = build_l8_unified_state(
        l3_stack,
        safety_stack,
        observability_streams,
        base_dir=base_dir,
        use_l2_coupling=use_l2_coupling,
        auto_collect=auto_collect,
    )
    return L8Reporter().build(state)
