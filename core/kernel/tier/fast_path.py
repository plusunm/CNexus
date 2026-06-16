"""T0 fast chat — single recall + chat, no DAG."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from core.kernel.context import ExecutionContext
from core.kernel.intent import ExecutionIntent
from core.kernel.router import route_intent

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def execute_fast_chat(
    intent: ExecutionIntent,
    ctx: ExecutionContext,
    runtime: "BrainMemoryRuntime",
) -> Any:
    payload = dict(intent.payload)
    message = str(payload.get("message") or "").strip()
    use_memory = payload.get("use_memory", True)

    meta = dict(payload.get("metadata") or {})
    if use_memory and message:
        recall = runtime.recall(
            message,
            top_k=payload.get("top_k"),
            use_attention=payload.get("use_attention", True),
            mutate_state=False,
        )
        if isinstance(recall, str) and recall.strip():
            meta["recall_prefetch"] = recall[:2000]

    payload["metadata"] = meta
    fast_intent = ExecutionIntent(
        type=intent.type,
        payload=payload,
        trace_id=intent.trace_id,
        source=intent.source,
        metadata=intent.metadata,
    )
    return route_intent(fast_intent, ctx, runtime)
