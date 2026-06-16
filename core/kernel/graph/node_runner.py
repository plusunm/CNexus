"""Shared graph node execution — used by scheduler v1 and v2."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from core.kernel.context import ExecutionContext
from core.kernel.intent import ExecutionIntent
from core.kernel.router import route_intent

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime
    from core.kernel.graph.execution_graph import KernelGraphNode


def prepare_intent(node: "KernelGraphNode", node_results: dict[str, Any]) -> ExecutionIntent:
    intent = node.intent
    payload = dict(intent.payload)

    if node.depends_on:
        upstream = {dep: node_results.get(dep) for dep in node.depends_on}
        payload["_upstream"] = upstream
        recall_hits = upstream.get(node.depends_on[0])
        if intent.type == "chat" and isinstance(recall_hits, str) and recall_hits.strip():
            meta = dict(payload.get("metadata") or {})
            meta["recall_prefetch"] = recall_hits[:2000]
            payload["metadata"] = meta
            return ExecutionIntent(
                type=intent.type,
                payload=payload,
                trace_id=intent.trace_id,
                source=intent.source,
                metadata=intent.metadata,
            )

    return intent


def resolve_join_inputs(
    node: "KernelGraphNode",
    node_results: dict[str, Any],
    *,
    require_success: bool = True,
) -> dict[str, Any] | None:
    """Join barrier — returns None when dependencies are not satisfied."""
    if not node.depends_on:
        return {}

    inputs: dict[str, Any] = {}
    for dep in node.depends_on:
        if dep not in node_results:
            return None
        entry = node_results[dep]
        if isinstance(entry, dict) and entry.get("_failed"):
            if require_success:
                return None
            inputs[dep] = entry.get("output")
            continue
        inputs[dep] = entry.get("output") if isinstance(entry, dict) and "output" in entry else entry
    return inputs


def execute_node(
    node: "KernelGraphNode",
    ctx: ExecutionContext,
    runtime: "BrainMemoryRuntime",
    node_results: dict[str, Any],
) -> Any:
    child_ctx = ExecutionContext(
        trace_id=ctx.trace_id,
        identity_id=ctx.identity_id,
        tags={**ctx.tags, "graph_node": node.node_id, "graph_label": node.label},
    )
    intent = prepare_intent(node, _outputs_only(node_results))
    return route_intent(intent, child_ctx, runtime)


def _outputs_only(node_results: dict[str, Any]) -> dict[str, Any]:
    outputs: dict[str, Any] = {}
    for key, value in node_results.items():
        if isinstance(value, dict) and "output" in value:
            outputs[key] = value["output"]
        else:
            outputs[key] = value
    return outputs


def wrap_node_result(output: Any, *, success: bool = True, error: str | None = None) -> dict[str, Any]:
    return {
        "output": output,
        "success": success,
        "error": error,
        "_failed": not success,
    }
