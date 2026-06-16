"""IR DAG schema — execution contract G (immutable during run)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple


class IRLayer(str, Enum):
    CS = "CS"
    ES = "ES"
    TOOL = "TOOL"


class IROp(str, Enum):
    INPUT = "INPUT"
    RETRIEVE = "RETRIEVE"
    FILTER = "FILTER"
    BUILD_CONTEXT = "BUILD_CONTEXT"
    CALL_LLM = "CALL_LLM"
    GOVERN = "GOVERN"
    REDUCE = "REDUCE"
    CAPTURE = "CAPTURE"


V1_OPS = frozenset(op.value for op in IROp)

OP_LAYER: Dict[str, IRLayer] = {
    IROp.INPUT.value: IRLayer.CS,
    IROp.RETRIEVE.value: IRLayer.CS,
    IROp.FILTER.value: IRLayer.CS,
    IROp.BUILD_CONTEXT.value: IRLayer.CS,
    IROp.GOVERN.value: IRLayer.CS,
    IROp.REDUCE.value: IRLayer.CS,
    IROp.CALL_LLM.value: IRLayer.ES,
    IROp.CAPTURE.value: IRLayer.TOOL,
}


@dataclass
class IRNode:
    id: str
    op: str
    params: Dict[str, Any] = field(default_factory=dict)
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)

    @property
    def layer(self) -> IRLayer:
        return OP_LAYER.get(self.op, IRLayer.CS)


@dataclass
class IRGraph:
    version: str
    graph_id: str
    template_name: str
    template_version: str
    nodes: Dict[str, IRNode]
    edges: List[Tuple[str, str]]

    def dependency_map(self) -> Dict[str, set[str]]:
        deps: Dict[str, set[str]] = {nid: set() for nid in self.nodes}
        for src, dst in self.edges:
            if dst in deps:
                deps[dst].add(src)
        return deps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "graph_id": self.graph_id,
            "template_name": self.template_name,
            "template_version": self.template_version,
            "nodes": [
                {
                    "id": n.id,
                    "op": n.op,
                    "params": n.params,
                    "inputs": n.inputs,
                    "outputs": n.outputs,
                    "layer": n.layer.value,
                }
                for n in self.nodes.values()
            ],
            "edges": [{"from": a, "to": b} for a, b in self.edges],
        }
