"""Graph + step verifier V."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

from ir_kernel.schema.graph import IRGraph, V1_OPS
from ir_kernel.schema.sigma_exec import SigmaExec


@dataclass
class VerifyResult:
    ok: bool
    errors: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {"ok": self.ok, "errors": list(self.errors)}


class GraphVerifier:
    def verify_graph(self, graph: IRGraph) -> VerifyResult:
        errors: List[str] = []
        if not graph.nodes:
            errors.append("empty_graph")

        for node in graph.nodes.values():
            if node.op not in V1_OPS:
                errors.append(f"unknown_op:{node.id}:{node.op}")

        for src, dst in graph.edges:
            if src not in graph.nodes or dst not in graph.nodes:
                errors.append(f"invalid_edge:{src}->{dst}")

        if self._has_cycle(graph):
            errors.append("cycle_detected")

        order = self._topological_sort(graph)
        if len(order) != len(graph.nodes) and "cycle_detected" not in errors:
            errors.append("unreachable_nodes")

        return VerifyResult(ok=len(errors) == 0, errors=errors)

    def verify_budget_pre(self, sigma: SigmaExec, op: str) -> VerifyResult:
        errors: List[str] = []
        budget = sigma.cost.get("budget") or {}
        if op == "CALL_LLM":
            max_calls = int(budget.get("max_llm_calls", 1))
            if int(sigma.cost.get("llm_calls", 0)) >= max_calls:
                errors.append("LLM_BUDGET_EXCEEDED")
        remaining = int(sigma.cost.get("remaining_tokens", 8000))
        if remaining <= 0:
            errors.append("BUDGET_EXCEEDED")
        return VerifyResult(ok=len(errors) == 0, errors=errors)

    def verify_step_post(self, sigma: SigmaExec, output: str) -> VerifyResult:
        errors: List[str] = []
        if output is None:
            errors.append("null_output")
        return VerifyResult(ok=len(errors) == 0, errors=errors)

    @staticmethod
    def _has_cycle(graph: IRGraph) -> bool:
        deps = graph.dependency_map()
        visiting: Set[str] = set()
        done: Set[str] = set()

        def dfs(nid: str) -> bool:
            if nid in visiting:
                return True
            if nid in done:
                return False
            visiting.add(nid)
            for pred in deps.get(nid, set()):
                if dfs(pred):
                    return True
            visiting.remove(nid)
            done.add(nid)
            return False

        return any(dfs(nid) for nid in graph.nodes)

    @staticmethod
    def _topological_sort(graph: IRGraph) -> List[str]:
        deps = graph.dependency_map()
        in_degree = {nid: len(deps[nid]) for nid in graph.nodes}
        ready = [nid for nid, d in in_degree.items() if d == 0]
        order: List[str] = []
        children: Dict[str, List[str]] = {nid: [] for nid in graph.nodes}
        for src, dst in graph.edges:
            children[src].append(dst)

        while ready:
            nid = ready.pop(0)
            order.append(nid)
            for child in children.get(nid, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    ready.append(child)
        return order
