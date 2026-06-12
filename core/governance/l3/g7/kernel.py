"""L3-G7 — layerless kernel engine (field collapse from L3 stack projection)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.g7.types import (
    AttractorNode,
    FieldState,
    G7_META_CONSTRAINTS,
    LayerlessKernelState,
    TraceEvent,
)


class LayerlessKernelEngine:
    """
    G7: No layers exist.
    Only field dynamics + attractor behavior + trace flow.
    """

    def project_from_l3_stack(self, l3_bundle: dict[str, Any]) -> LayerlessKernelState:
        field = FieldState(
            intensity=self._compute_intensity(l3_bundle),
            entropy=self._compute_entropy(l3_bundle),
            coherence=self._compute_coherence(l3_bundle),
        )
        attractors = self._extract_attractors(l3_bundle)
        traces = self._extract_traces(l3_bundle)

        return LayerlessKernelState(
            field=field,
            attractors=attractors,
            traces=traces,
            metadata={
                "model": "L3-G7",
                "layer_abstraction": "NONE",
                **G7_META_CONSTRAINTS,
            },
        )

    def _compute_intensity(self, bundle: dict[str, Any]) -> float:
        return round(float(bundle.get("coupling_strength", 0.5)), 4)

    def _compute_entropy(self, bundle: dict[str, Any]) -> float:
        return round(float(bundle.get("drift_index", 0.5)), 4)

    def _compute_coherence(self, bundle: dict[str, Any]) -> float:
        return round(float(bundle.get("stability_score", 0.5)), 4)

    def _extract_attractors(self, bundle: dict[str, Any]) -> list[AttractorNode]:
        raw = bundle.get("attractors") or []
        nodes: list[AttractorNode] = []
        for item in raw:
            if isinstance(item, AttractorNode):
                nodes.append(item)
            elif isinstance(item, dict):
                nodes.append(
                    AttractorNode(
                        attractor_id=str(item.get("id", item.get("attractor_id", "unknown"))),
                        strength=float(item.get("strength", 0.5)),
                        basin=str(item.get("basin", "diffuse")),
                    )
                )
        return nodes

    def _extract_traces(self, bundle: dict[str, Any]) -> list[TraceEvent]:
        raw = bundle.get("trace_events") or []
        traces: list[TraceEvent] = []
        for item in raw:
            if isinstance(item, TraceEvent):
                traces.append(item)
            elif isinstance(item, dict):
                traces.append(
                    TraceEvent(
                        timestamp=float(item.get("timestamp", 0.0)),
                        signal_type=str(item.get("signal_type", "observation")),
                        payload=dict(item.get("payload", item)),
                    )
                )
        return traces
