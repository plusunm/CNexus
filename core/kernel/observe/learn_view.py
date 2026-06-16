"""Learn Mode observation — cognitive projection from ExecutionRecord."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from core.kernel.learn.interpreter import LearnExplanationV2, interpret_v2

if TYPE_CHECKING:
    from core.kernel.kernel import ExecutionKernel


def read_learn(trace_id: str, kernel: "ExecutionKernel") -> LearnExplanationV2:
    record = kernel.get_record(trace_id)
    if record is not None:
        return interpret_v2(record)
    from core.kernel.observe.tap_fallback import interpret_v2_from_tap, tap_events_for_trace

    events = tap_events_for_trace(trace_id)
    if events:
        return interpret_v2_from_tap(trace_id, events)
    raise KeyError(f"execution record not found: {trace_id}")


def read_learn_dict(trace_id: str, kernel: "ExecutionKernel") -> dict[str, Any]:
    return read_learn(trace_id, kernel).to_dict()
