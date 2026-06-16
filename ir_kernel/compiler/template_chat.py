"""Bootstrap chat DAG — v1 executable graph."""

from __future__ import annotations

from ir_kernel.compiler.registry import compute_graph_id, register
from ir_kernel.schema.graph import IRGraph, IRNode, IROp


TEMPLATE_NAME = "chat_single_turn"
TEMPLATE_VERSION = "1.0.0"


def _linear_chat_graph(*, use_memory: bool = True) -> IRGraph:
    nodes = {
        "n0": IRNode("n0", IROp.INPUT.value, outputs=["input"]),
        "n1": IRNode("n1", IROp.RETRIEVE.value, outputs=["context_raw"], params={"use_memory": use_memory}),
        "n2": IRNode("n2", IROp.FILTER.value, outputs=["context"]),
        "n3": IRNode("n3", IROp.BUILD_CONTEXT.value, outputs=["context"]),
        "n4": IRNode("n4", IROp.CALL_LLM.value, outputs=["llm_output"]),
        "n5": IRNode("n5", IROp.GOVERN.value, outputs=["reply"]),
        "n6": IRNode("n6", IROp.REDUCE.value, outputs=["final"]),
    }
    edges = [
        ("n0", "n1"),
        ("n1", "n2"),
        ("n2", "n3"),
        ("n3", "n4"),
        ("n4", "n5"),
        ("n5", "n6"),
    ]
    payload = {"use_memory": use_memory, "nodes": len(nodes)}
    graph_id = compute_graph_id(TEMPLATE_NAME, TEMPLATE_VERSION, payload)
    return IRGraph(
        version="cnexus-ir-1.0",
        graph_id=graph_id,
        template_name=TEMPLATE_NAME,
        template_version=TEMPLATE_VERSION,
        nodes=nodes,
        edges=edges,
    )


def compile_chat_single_turn(*, use_memory: bool = True) -> IRGraph:
    return _linear_chat_graph(use_memory=use_memory)


register(TEMPLATE_NAME, compile_chat_single_turn)
