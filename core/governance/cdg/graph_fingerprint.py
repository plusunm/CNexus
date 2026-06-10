"""Deterministic causal graph fingerprint for audit replay / L7 proof."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import networkx as nx


def graph_fingerprint(graph: "nx.DiGraph") -> str:
    """
    Stable SHA-256 over sorted nodes + edges (process-independent).

    Format: N:{node|node...}#E:{parent>child|...}
    """
    nodes = "|".join(sorted(str(n) for n in graph.nodes()))
    edges = "|".join(
        f"{u}>{v}" for u, v in sorted((str(u), str(v)) for u, v in graph.edges())
    )
    payload = f"N:{nodes}#E:{edges}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
