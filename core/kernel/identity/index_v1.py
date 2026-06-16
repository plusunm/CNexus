"""Identity Graph Index v1 — cross-trace equivalence retrieval."""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from core.kernel.graph.execution_graph import KernelExecutionGraph
from core.kernel.identity.graph_identity_v1 import GraphIdentityV1

_index: Optional["IdentityGraphIndexV1"] = None
_index_lock = threading.Lock()


class IdentityGraphIndexV1:
    """
    CP-3 Identity Index Layer v1.

    - trace → identity
    - identity → trace[]
    - cross-trace equivalence retrieval
    """

    def __init__(self) -> None:
        self.identity_kernel = GraphIdentityV1()
        self._index: dict[str, list[str]] = defaultdict(list)
        self._reverse_index: dict[str, str] = {}
        self._lock = threading.Lock()
        self._persist_path: Optional[Path] = None

    def set_persist_base(self, base_dir: str | Path) -> None:
        root = Path(base_dir) / "observability"
        root.mkdir(parents=True, exist_ok=True)
        self._persist_path = root / "graph_identity_index.jsonl"

    def register(self, trace_id: str, graph: KernelExecutionGraph) -> str:
        identity = self.identity_kernel.compute_identity(graph)
        with self._lock:
            traces = self._index[identity]
            if trace_id not in traces:
                traces.append(trace_id)
            self._reverse_index[trace_id] = identity
        self._append_row(
            {
                "identity": identity,
                "trace_id": trace_id,
                "graph_invariant": graph.invariant_hash(),
                "ts": time.time(),
            }
        )
        return identity

    def get_identity(self, trace_id: str) -> Optional[str]:
        with self._lock:
            return self._reverse_index.get(trace_id)

    def get_traces(self, identity: str) -> list[str]:
        with self._lock:
            return list(self._index.get(identity, []))

    def find_equivalent_traces(
        self,
        graph: KernelExecutionGraph,
        *,
        exclude_trace: str | None = None,
    ) -> dict[str, Any]:
        identity = self.identity_kernel.compute_identity(graph)
        with self._lock:
            traces = list(self._index.get(identity, []))
        if exclude_trace:
            traces = [t for t in traces if t != exclude_trace]
        return {
            "identity": identity,
            "equivalent_traces": traces,
            "count": len(traces),
            "is_new": len(traces) == 0,
            "version": "graph-identity-index-v1",
        }

    def stats(self) -> dict[str, Any]:
        with self._lock:
            classes = list(self._index.values())
            return {
                "unique_identities": len(self._index),
                "total_traces": len(self._reverse_index),
                "largest_equivalence_class": max((len(v) for v in classes), default=0),
            }

    def hydrate_from_disk(self) -> int:
        if not self._persist_path or not self._persist_path.exists():
            return 0
        loaded = 0
        with self._lock:
            with open(self._persist_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    identity = str(row.get("identity") or "")
                    trace_id = str(row.get("trace_id") or "")
                    if not identity or not trace_id:
                        continue
                    traces = self._index[identity]
                    if trace_id not in traces:
                        traces.append(trace_id)
                    self._reverse_index[trace_id] = identity
                    loaded += 1
        return loaded

    def _append_row(self, row: dict[str, Any]) -> None:
        if not self._persist_path:
            return
        with open(self._persist_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def get_identity_graph_index() -> IdentityGraphIndexV1:
    global _index
    with _index_lock:
        if _index is None:
            _index = IdentityGraphIndexV1()
        return _index


def configure_identity_graph_index(base_dir: str) -> None:
    index = get_identity_graph_index()
    index.set_persist_base(base_dir)
    index.hydrate_from_disk()


def reset_identity_graph_index() -> None:
    global _index
    with _index_lock:
        _index = IdentityGraphIndexV1()
