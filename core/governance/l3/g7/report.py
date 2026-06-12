"""L3-G7 — layerless kernel report synthesis."""

from __future__ import annotations

from typing import Any

from core.governance.l3.g7.types import G7_META_CONSTRAINTS, L3G7Report, LayerlessKernelState


class L3G7Reporter:
    def build(self, state: LayerlessKernelState, interpretation: dict[str, Any]) -> L3G7Report:
        metadata = {**state.metadata, **G7_META_CONSTRAINTS}
        return L3G7Report(
            model="L3-G7 Layerless Kernel",
            field=state.field.to_dict(),
            attractors=len(state.attractors),
            traces=len(state.traces),
            interpretation_mode="non-layered",
            interpretation=interpretation,
            metadata=metadata,
        )
