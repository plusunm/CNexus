"""Dependency resolution — topo sort, ready-set, acyclic validation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.kernel.graph.execution_graph import KernelExecutionGraph, KernelGraphNode


class GraphResolutionError(Exception):
    pass


def build_dependency_map(graph: "KernelExecutionGraph") -> dict[str, set[str]]:
    deps: dict[str, set[str]] = {n.node_id: set(n.depends_on) for n in graph.nodes}
    for edge in graph.edges:
        if edge.kind in ("depends", "join", "causal"):
            deps.setdefault(edge.to_id, set()).add(edge.from_id)
    return deps


def validate_acyclic(graph: "KernelExecutionGraph") -> None:
    deps = build_dependency_map(graph)
    visited: set[str] = set()
    stack: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in stack:
            raise GraphResolutionError(f"cycle detected at node {node_id}")
        if node_id in visited:
            return
        stack.add(node_id)
        for dep in deps.get(node_id, set()):
            visit(dep)
        stack.remove(node_id)
        visited.add(node_id)

    for node in graph.nodes:
        visit(node.node_id)


def topological_generations(graph: "KernelExecutionGraph") -> list[list[str]]:
    """Return execution waves — nodes in the same wave may run concurrently."""
    validate_acyclic(graph)
    deps = build_dependency_map(graph)
    remaining = {n.node_id for n in graph.nodes}
    completed: set[str] = set()
    generations: list[list[str]] = []

    while remaining:
        ready = sorted(nid for nid in remaining if deps.get(nid, set()).issubset(completed))
        if not ready:
            raise GraphResolutionError("deadlock — no ready nodes")
        generations.append(ready)
        completed.update(ready)
        remaining -= set(ready)
    return generations


def topological_order(graph: "KernelExecutionGraph") -> list["KernelGraphNode"]:
    """Linear topo order for sequential scheduler v1."""
    generations = topological_generations(graph)
    node_map = graph.node_map()
    order: list[KernelGraphNode] = []
    for wave in generations:
        for nid in wave:
            order.append(node_map[nid])
    return order


def get_ready_nodes(graph: "KernelExecutionGraph") -> list["KernelGraphNode"]:
    deps = build_dependency_map(graph)
    completed = {n.node_id for n in graph.nodes if n.status == "done"}
    pending = [n for n in graph.nodes if n.status == "pending"]
    return [n for n in pending if deps.get(n.node_id, set()).issubset(completed)]
