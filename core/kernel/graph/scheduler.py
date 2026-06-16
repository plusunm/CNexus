"""Graph scheduler — topo-order execution with dependency injection."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from core.kernel.context import ExecutionContext
from core.kernel.graph.node_runner import execute_node
from core.kernel.graph.resolver import GraphResolutionError, get_ready_nodes, validate_acyclic

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime
    from core.kernel.graph.execution_graph import KernelExecutionGraph, KernelGraphNode


class GraphScheduler:
    """Execute KernelExecutionGraph — v1 sequential ready-set loop."""

    def run(
        self,
        graph: "KernelExecutionGraph",
        ctx: ExecutionContext,
        runtime: "BrainMemoryRuntime",
    ) -> Any:
        validate_acyclic(graph)
        node_results: dict[str, Any] = {}

        while True:
            ready = get_ready_nodes(graph)
            if not ready:
                pending = [n for n in graph.nodes if n.status == "pending"]
                if pending:
                    raise GraphResolutionError("scheduler stalled with pending nodes")
                break

            for node in ready:
                self._run_node(node, graph, ctx, runtime, node_results)

        sink_id = graph.sink_node_id()
        sink = graph.node_map().get(sink_id)
        if sink and sink.result is not None:
            return self._wrap_result(graph, sink.result)
        return self._wrap_result(graph, node_results)

    def _run_node(
        self,
        node: "KernelGraphNode",
        graph: "KernelExecutionGraph",
        ctx: ExecutionContext,
        runtime: "BrainMemoryRuntime",
        node_results: dict[str, Any],
    ) -> None:
        node.status = "running"
        child_ctx = ExecutionContext(
            trace_id=ctx.trace_id,
            identity_id=ctx.identity_id,
            tags={**ctx.tags, "graph_node": node.node_id, "graph_label": node.label},
        )

        try:
            result = execute_node(node, child_ctx, runtime, node_results)
            node.result = result
            node.status = "done"
            node_results[node.node_id] = result
        except Exception as exc:
            node.status = "failed"
            node.error = str(exc)
            raise

    def _wrap_result(self, graph: "KernelExecutionGraph", result: Any) -> Any:
        if len(graph.nodes) == 1:
            return result
        if isinstance(result, dict):
            wrapped = dict(result)
            wrapped.setdefault("execution_graph", graph.to_dict())
            wrapped.setdefault("graph_invariant", graph.invariant_hash())
            return wrapped
        return {
            "result": result,
            "execution_graph": graph.to_dict(),
            "graph_invariant": graph.invariant_hash(),
            "trace_id": graph.trace_id,
        }
