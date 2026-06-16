"""CNexus IR execution kernel — Σ_exec DAG runtime over BrainMemoryRuntime adapters."""

from ir_kernel.engine import compile_and_execute, execute_graph
from ir_kernel.schema.graph import IRGraph

__all__ = ["IRGraph", "compile_and_execute", "execute_graph"]
