"""Scheduler v2 — wave-parallel execution with join barriers and failure propagation."""

from __future__ import annotations

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Literal, TYPE_CHECKING

from core.kernel.context import ExecutionContext
from core.kernel.graph.node_runner import execute_node, resolve_join_inputs, wrap_node_result
from core.kernel.graph.resolver import GraphResolutionError, topological_generations, validate_acyclic

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime
    from core.kernel.graph.execution_graph import KernelExecutionGraph, KernelGraphNode

logger = logging.getLogger("kernel.scheduler.v2")

FailurePolicy = Literal["fail_fast", "partial", "skip_dependents"]


@dataclass
class NodeResult:
    node_id: str
    output: Any
    success: bool = True
    error: str | None = None
    skipped: bool = False

    def to_store(self) -> dict[str, Any]:
        if self.skipped:
            return {"output": None, "success": False, "error": self.error, "_failed": True, "_skipped": True}
        return wrap_node_result(self.output, success=self.success, error=self.error)


def scheduler_v2_enabled() -> bool:
    flag = os.environ.get("USE_SCHEDULER_V2", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


class SchedulerV2:
    """
    Execution Graph Scheduler v2:
    - wave-based fan-out parallelism
    - join barrier resolution
    - failure propagation (fail_fast / partial / skip_dependents)
    """

    def __init__(
        self,
        *,
        max_parallelism: int = 8,
        failure_policy: FailurePolicy = "skip_dependents",
    ) -> None:
        self.max_parallelism = max(1, max_parallelism)
        self.failure_policy: FailurePolicy = failure_policy

    def run(
        self,
        graph: "KernelExecutionGraph",
        ctx: ExecutionContext,
        runtime: "BrainMemoryRuntime",
    ) -> Any:
        """Sync entry — kernel.execute() remains synchronous."""
        from core.runtime.async_bridge import run_coro_sync

        return run_coro_sync(self.run_async(graph, ctx, runtime))

    async def run_async(
        self,
        graph: "KernelExecutionGraph",
        ctx: ExecutionContext,
        runtime: "BrainMemoryRuntime",
    ) -> Any:
        validate_acyclic(graph)
        node_map = graph.node_map()
        generations = topological_generations(graph)
        node_results: dict[str, dict[str, Any]] = {}
        failed_ids: set[str] = set()
        skipped_ids: set[str] = set()

        logger.info("scheduler_v2 start trace=%s waves=%d", graph.trace_id, len(generations))

        for wave_idx, wave_ids in enumerate(generations):
            wave_nodes: list[KernelGraphNode] = []
            for node_id in wave_ids:
                node = node_map[node_id]
                if self._should_skip_node(node, failed_ids, skipped_ids, node_results):
                    node.status = "skipped"
                    node.error = "skipped: upstream failure"
                    skipped_ids.add(node_id)
                    node_results[node_id] = NodeResult(
                        node_id, None, success=False, error=node.error, skipped=True
                    ).to_store()
                    continue
                wave_nodes.append(node)

            if not wave_nodes:
                if self.failure_policy == "fail_fast" and (failed_ids or skipped_ids):
                    break
                continue

            logger.info("scheduler_v2 wave=%d nodes=%d", wave_idx, len(wave_nodes))
            wave_results = await self._execute_wave(wave_nodes, ctx, runtime, node_results)

            for result in wave_results:
                node = node_map[result.node_id]
                node_results[result.node_id] = result.to_store()
                if result.skipped:
                    node.status = "skipped"
                    skipped_ids.add(result.node_id)
                elif result.success:
                    node.status = "done"
                    node.result = result.output
                else:
                    node.status = "failed"
                    node.error = result.error
                    failed_ids.add(result.node_id)

                if self.failure_policy == "fail_fast" and not result.success:
                    logger.error("scheduler_v2 fail_fast at node=%s", result.node_id)
                    return self._build_final(graph, node_results, failed_ids, skipped_ids, halted=True)

        return self._build_final(graph, node_results, failed_ids, skipped_ids, halted=False)

    def _should_skip_node(
        self,
        node: "KernelGraphNode",
        failed_ids: set[str],
        skipped_ids: set[str],
        node_results: dict[str, dict[str, Any]],
    ) -> bool:
        if self.failure_policy == "partial":
            return False
        for dep in node.depends_on:
            if dep in failed_ids or dep in skipped_ids:
                return True
            dep_entry = node_results.get(dep)
            if dep_entry and dep_entry.get("_failed"):
                return True
        if resolve_join_inputs(node, node_results, require_success=self.failure_policy != "partial") is None:
            return bool(node.depends_on)
        return False

    async def _execute_wave(
        self,
        nodes: list["KernelGraphNode"],
        ctx: ExecutionContext,
        runtime: "BrainMemoryRuntime",
        node_results: dict[str, dict[str, Any]],
    ) -> list[NodeResult]:
        sem = asyncio.Semaphore(self.max_parallelism)
        loop = asyncio.get_running_loop()

        async def run_one(node: "KernelGraphNode") -> NodeResult:
            async with sem:
                node.status = "running"
                join_ready = resolve_join_inputs(node, node_results, require_success=True)
                if node.depends_on and join_ready is None:
                    return NodeResult(node.node_id, None, success=False, error="join barrier not satisfied")

                try:
                    output = await loop.run_in_executor(
                        None,
                        lambda: execute_node(node, ctx, runtime, node_results),
                    )
                    return NodeResult(node.node_id, output, True)
                except Exception as exc:
                    logger.exception("scheduler_v2 node failed %s", node.node_id)
                    return NodeResult(node.node_id, None, success=False, error=str(exc))

        return await asyncio.gather(*[run_one(n) for n in nodes])

    def _build_final(
        self,
        graph: "KernelExecutionGraph",
        node_results: dict[str, dict[str, Any]],
        failed_ids: set[str],
        skipped_ids: set[str],
        *,
        halted: bool,
    ) -> Any:
        outputs = {
            nid: entry.get("output")
            for nid, entry in node_results.items()
            if entry.get("success")
        }
        errors = {
            nid: entry.get("error")
            for nid, entry in node_results.items()
            if entry.get("_failed") and not entry.get("_skipped")
        }
        skipped = sorted(skipped_ids)

        sink_id = graph.sink_node_id()
        sink_entry = node_results.get(sink_id)
        sink_output = sink_entry.get("output") if sink_entry and sink_entry.get("success") else None

        meta = {
            "scheduler": "v2",
            "scheduler_version": "execution-scheduler-v2",
            "graph_invariant": graph.invariant_hash(),
            "execution_graph": graph.to_dict(),
            "trace_id": graph.trace_id,
            "waves_executed": len({n.status for n in graph.nodes}),
            "node_outputs": outputs,
            "node_errors": errors,
            "skipped_nodes": skipped,
            "halted": halted,
            "failure_policy": self.failure_policy,
        }

        if len(graph.nodes) == 1 and sink_output is not None and not failed_ids:
            return sink_output

        if isinstance(sink_output, dict):
            merged = dict(sink_output)
            merged.update(meta)
            return merged

        if sink_output is not None:
            return {**meta, "result": sink_output}

        return meta
