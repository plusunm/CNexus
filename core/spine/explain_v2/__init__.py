"""CP-2 Explanation Engine v2 — causal × state × control fusion."""

from __future__ import annotations

from typing import Any

from core.spine.explain_v2.control_index import ControlIndex
from core.spine.explain_v2.fusion import CausalStateFusionEngine
from core.spine.explain_v2.narrative import NarrativeSynthesizerV2
from core.spine.explain_v2.state_index import StateIndex
from core.spine.query.causal_index import CausalIndex

FUSION_VERSION = "explain-v2"


def build_fusion_explanation(
    trace_id: str,
    events: list[dict[str, Any]],
    *,
    causal_index: CausalIndex | None = None,
) -> dict[str, Any]:
    index = causal_index or CausalIndex()
    if causal_index is None:
        index.build(events)

    state_index = StateIndex()
    state_index.build(events)

    control_index = ControlIndex()
    control_index.build(events)

    fusion_engine = CausalStateFusionEngine()
    fused = fusion_engine.build(
        events,
        causal_index=index,
        state_index=state_index,
        control_index=control_index,
    )

    explanation = NarrativeSynthesizerV2().synthesize(
        trace_id=trace_id,
        causal_chain=fused["causal_chain"],
        state_transitions=fused["state_transitions"],
        control_flow=fused["control_flow"],
    )

    return {
        "version": FUSION_VERSION,
        "trace_id": trace_id,
        "causal_chain": fused["causal_chain"],
        "state_transitions": fused["state_transitions"],
        "control_flow": fused["control_flow"],
        "explanation": explanation,
    }
