"""Intent → KernelExecutionGraph builder."""

from __future__ import annotations

from typing import Any

from core.kernel.graph.execution_graph import (
    KernelExecutionGraph,
    KernelGraphEdge,
    KernelGraphNode,
    new_node_id,
)
from core.kernel.intent import ExecutionIntent


class GraphBuilder:
    """Expand a root intent into an execution DAG."""

    def build(
        self,
        intent: ExecutionIntent,
        trace_id: str,
        *,
        tier: str | None = None,
    ) -> KernelExecutionGraph:
        effective_tier = tier or "T3"
        if (
            intent.type == "chat"
            and effective_tier == "T3"
            and intent.payload.get("_action") not in (
                "prepare",
                "confirm",
                "cancel",
            )
        ):
            return self._build_chat_with_memory(intent, trace_id)
        return self._build_single(intent, trace_id)

    def _build_single(self, intent: ExecutionIntent, trace_id: str) -> KernelExecutionGraph:
        node_id = new_node_id()
        node = KernelGraphNode(
            node_id=node_id,
            intent=intent,
            label=intent.type,
        )
        return KernelExecutionGraph(
            trace_id=trace_id,
            nodes=[node],
            root_node_ids=[node_id],
            join_node_id=node_id,
        )

    def _build_chat_with_memory(self, intent: ExecutionIntent, trace_id: str) -> KernelExecutionGraph:
        """Fork: recall ∥ (optional) → join → chat."""
        message = str(intent.payload.get("message") or "")
        use_memory = intent.payload.get("use_memory", True)

        if not use_memory or not message.strip():
            return self._build_single(intent, trace_id)

        recall_id = new_node_id("recall")
        chat_id = new_node_id("chat")

        recall_intent = ExecutionIntent(
            type="recall",
            payload={
                "query": message,
                "top_k": intent.payload.get("top_k"),
                "use_attention": intent.payload.get("use_attention", True),
                "mutate_state": False,
            },
            trace_id=trace_id,
            source=intent.source,
            metadata={"graph_role": "prefetch"},
        )
        chat_intent = ExecutionIntent(
            type="chat",
            payload=dict(intent.payload),
            trace_id=trace_id,
            source=intent.source,
            metadata={"graph_role": "sink"},
        )

        recall_node = KernelGraphNode(
            node_id=recall_id,
            intent=recall_intent,
            label="recall_prefetch",
        )
        chat_node = KernelGraphNode(
            node_id=chat_id,
            intent=chat_intent,
            label="chat_send",
            depends_on=[recall_id],
        )

        edge = KernelGraphEdge(from_id=recall_id, to_id=chat_id, kind="join", relation="memory_context")

        return KernelExecutionGraph(
            trace_id=trace_id,
            nodes=[recall_node, chat_node],
            edges=[edge],
            root_node_ids=[recall_id],
            join_node_id=chat_id,
        )

    def build_from_plan(self, trace_id: str, nodes: list[dict[str, Any]]) -> KernelExecutionGraph:
        """Explicit multi-node plan for advanced callers."""
        built_nodes: list[KernelGraphNode] = []
        id_map: dict[str, str] = {}

        for spec in nodes:
            local_id = str(spec.get("id") or new_node_id())
            id_map[local_id] = local_id
            built_nodes.append(
                KernelGraphNode(
                    node_id=local_id,
                    intent=ExecutionIntent.from_dict(spec["intent"]),
                    label=str(spec.get("label") or spec["intent"]["type"]),
                    depends_on=[str(d) for d in spec.get("depends_on") or []],
                )
            )

        edges = [
            KernelGraphEdge(from_id=str(e["from"]), to_id=str(e["to"]), kind=e.get("kind", "depends"))
            for e in (nodes[0].get("_edges") if nodes else []) or []
        ]
        # edges from depends_on if not explicit
        if not edges:
            for node in built_nodes:
                for dep in node.depends_on:
                    edges.append(KernelGraphEdge(from_id=dep, to_id=node.node_id, kind="depends"))

        roots = [n.node_id for n in built_nodes if not n.depends_on]
        sink = built_nodes[-1].node_id if built_nodes else None
        return KernelExecutionGraph(
            trace_id=trace_id,
            nodes=built_nodes,
            edges=edges,
            root_node_ids=roots,
            join_node_id=sink,
        )
