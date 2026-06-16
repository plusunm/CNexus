"""Full cognitive chat graph — same DAG, distinct template id for parity tests."""

from __future__ import annotations

from ir_kernel.compiler.registry import compute_graph_id, register
from ir_kernel.compiler.template_chat import _linear_chat_graph
from ir_kernel.schema.graph import IRGraph

TEMPLATE_NAME = "cognitive_chat_full"
TEMPLATE_VERSION = "1.0.0"


def compile_cognitive_chat_full(*, use_memory: bool = True) -> IRGraph:
    graph = _linear_chat_graph(use_memory=use_memory)
    payload = {"use_memory": use_memory, "profile": "cognitive_full"}
    graph_id = compute_graph_id(TEMPLATE_NAME, TEMPLATE_VERSION, payload)
    return IRGraph(
        version=graph.version,
        graph_id=graph_id,
        template_name=TEMPLATE_NAME,
        template_version=TEMPLATE_VERSION,
        nodes=graph.nodes,
        edges=graph.edges,
    )


register(TEMPLATE_NAME, compile_cognitive_chat_full)
