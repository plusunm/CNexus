"""T1 light chat — no graph, memory disabled."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from core.kernel.context import ExecutionContext
from core.kernel.intent import ExecutionIntent
from core.kernel.router import route_intent

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def execute_minimal(
    intent: ExecutionIntent,
    ctx: ExecutionContext,
    runtime: "BrainMemoryRuntime",
) -> Any:
    payload = dict(intent.payload)
    payload["use_memory"] = False
    light_intent = ExecutionIntent(
        type=intent.type,
        payload=payload,
        trace_id=intent.trace_id,
        source=intent.source,
        metadata=intent.metadata,
    )
    return route_intent(light_intent, ctx, runtime)
