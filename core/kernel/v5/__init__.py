"""CNexus Non-Hang Kernel v5 — cross-machine cluster + CRDT + consensus."""

from core.kernel.v5.cluster_consensus import ClusterConsensus
from core.kernel.v5.crdt_memory import CRDTMemory, get_crdt_memory
from core.kernel.v5.global_cluster_runtime import GlobalClusterRuntime, get_global_cluster_runtime

__all__ = [
    "CRDTMemory",
    "ClusterConsensus",
    "GlobalClusterRuntime",
    "get_crdt_memory",
    "get_global_cluster_runtime",
]
