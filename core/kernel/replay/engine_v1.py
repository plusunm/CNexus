"""Execution Graph Replay Engine v1 — re-execute and verify identity consistency."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, TYPE_CHECKING

from core.kernel.context import ExecutionContext
from core.kernel.graph.execution_graph import KernelExecutionGraph
from core.kernel.hooks import record_execution_tap
from core.kernel.identity.index_v1 import IdentityGraphIndexV1
from core.kernel.record import ExecutionRecord

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime
    from core.kernel.graph.scheduler_v2 import SchedulerV2


class ExecutionGraphReplayEngineV1:
    """
    CP-3 Replay Engine v1.

    - Re-run execution graph through scheduler v2
    - Verify identity consistency against indexed trace
    - Emit replay tap events
    """

    def __init__(
        self,
        scheduler: "SchedulerV2",
        identity_index: IdentityGraphIndexV1,
        runtime: "BrainMemoryRuntime",
    ) -> None:
        self.scheduler = scheduler
        self.identity_index = identity_index
        self.runtime = runtime

    def replay(
        self,
        graph: KernelExecutionGraph,
        *,
        verify_identity: bool = True,
        trace_id: str | None = None,
        source: str = "replay",
    ) -> dict[str, Any]:
        replay_graph = copy.deepcopy(graph)
        replay_trace = trace_id or f"{graph.trace_id}:replay"

        ctx = ExecutionContext(
            trace_id=replay_trace,
            tags={"source": source, "intent": "replay"},
        )

        replay_result = self.scheduler.run(replay_graph, ctx, self.runtime)

        replay_identity = self.identity_index.identity_kernel.compute_identity(replay_graph)
        original_identity = self.identity_index.get_identity(trace_id) if trace_id else None

        identity_match: bool | None = None
        if verify_identity and original_identity:
            identity_match = original_identity == replay_identity

        replay_signature = self._replay_signature(replay_graph, replay_identity)
        status = self._status(identity_match, verify_identity)

        record_execution_tap(
            {
                "trace_id": replay_trace,
                "phase": "execution_replay",
                "identity": replay_identity,
                "original_identity": original_identity,
                "identity_match": identity_match,
                "replay_status": status,
                "replay_signature": replay_signature,
            }
        )

        return {
            "replay_result": replay_result,
            "identity": replay_identity,
            "original_identity": original_identity,
            "identity_match": identity_match,
            "replay_status": status,
            "replay_signature": replay_signature,
            "replay_trace_id": replay_trace,
            "version": "execution-replay-v1",
        }

    def replay_record(
        self,
        record: ExecutionRecord,
        *,
        verify_identity: bool = True,
    ) -> dict[str, Any]:
        graph = self._graph_from_record(record)
        return self.replay(
            graph,
            verify_identity=verify_identity,
            trace_id=record.trace_id,
        )

    def _graph_from_record(self, record: ExecutionRecord) -> KernelExecutionGraph:
        from core.kernel.intent import ExecutionIntent
        from core.kernel.graph.execution_graph import KernelGraphEdge, KernelGraphNode

        if not record.graph:
            raise ValueError("execution record has no graph to replay")

        nodes: list[KernelGraphNode] = []
        for row in record.nodes:
            intent_data = row.get("intent") or {}
            nodes.append(
                KernelGraphNode(
                    node_id=str(row.get("node_id") or ""),
                    intent=ExecutionIntent.from_dict(intent_data),
                    label=str(row.get("label") or ""),
                    depends_on=[str(d) for d in row.get("depends_on") or []],
                    status="pending",
                )
            )

        edges = [
            KernelGraphEdge(
                from_id=str(e.get("from_id") or ""),
                to_id=str(e.get("to_id") or ""),
                kind=e.get("kind", "depends"),
                relation=e.get("relation"),
            )
            for e in record.edges
        ]

        return KernelExecutionGraph(
            trace_id=record.trace_id,
            nodes=nodes,
            edges=edges,
            root_node_ids=list((record.graph or {}).get("roots") or []),
            join_node_id=(record.graph or {}).get("join"),
        )

    def _replay_signature(self, graph: KernelExecutionGraph, identity: str) -> str:
        payload = {
            "identity": identity,
            "graph_invariant": graph.invariant_hash(),
            "node_count": len(graph.nodes),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return f"R-{digest[:16]}"

    def _status(self, identity_match: bool | None, verify: bool) -> str:
        if not verify or identity_match is None:
            return "replayed"
        return "consistent" if identity_match else "divergent"
