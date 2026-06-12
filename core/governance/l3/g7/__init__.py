"""L3-G7 — layerless kernel (field-native cognition, no hierarchy)."""

from __future__ import annotations

from typing import Any

from core.governance.l3.g7.bundle import derive_l3_bundle_from_stack
from core.governance.l3.g7.interpreter import LayerlessInterpreter
from core.governance.l3.g7.kernel import LayerlessKernelEngine
from core.governance.l3.g7.report import L3G7Reporter
from core.governance.l3.g7.types import (
    AttractorNode,
    FieldState,
    G7_META_CONSTRAINTS,
    L3G7Report,
    LayerlessKernelState,
    TraceEvent,
)

__all__ = [
    "AttractorNode",
    "FieldState",
    "G7_META_CONSTRAINTS",
    "L3G7Report",
    "L3G7Reporter",
    "LayerlessInterpreter",
    "LayerlessKernelEngine",
    "LayerlessKernelState",
    "TraceEvent",
    "build_l3_g7_report",
    "derive_l3_bundle_from_stack",
]


def build_l3_g7_report(l3_bundle: dict[str, Any]) -> L3G7Report:
    engine = LayerlessKernelEngine()
    interpreter = LayerlessInterpreter()
    reporter = L3G7Reporter()

    state = engine.project_from_l3_stack(l3_bundle)
    interpretation = interpreter.interpret(state)
    return reporter.build(state, interpretation)
