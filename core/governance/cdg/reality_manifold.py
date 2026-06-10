"""Reality Manifold — COOS-level causal observability kernel (v3.4)."""

from __future__ import annotations

import logging
import math
import time
import uuid
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

logger = logging.getLogger("G1.CDG.RealityManifold")


@dataclass
class RealityFrame:
    event_id: str
    parent_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"

    @property
    def event_type(self) -> str:
        return str(self.payload.get("event_type", self.source))

    @classmethod
    def from_action(
        cls,
        text: str,
        *,
        event_type: str = "user_action",
        event_id: str | None = None,
        parent_id: str | None = None,
        replay_ref: str | None = None,
        source: str | None = None,
        **payload: Any,
    ) -> "RealityFrame":
        body = {"text": text, "event_type": event_type, **payload}
        if replay_ref is not None:
            body["replay_ref"] = replay_ref
        return cls(
            event_id=event_id or str(uuid.uuid4()),
            parent_id=parent_id,
            payload=body,
            timestamp=time.time(),
            source=source or ("user_action" if event_type == "user_action" else event_type),
        )


class RealityManifold:
    """
    COOS-level causal observability kernel (v3.4).

    - Strict frame / graph separation (payload in frames, topology in graph)
    - Online source entropy + entropy_rate
    - Causal-safe leaf pruning with counter sync
    - Path-aware grounding (nx ancestors + shortest-path decay)
    - Entropy dynamics: piecewise (ΔH across ingest/prune steps)
    """

    GROUNDED_SOURCES = frozenset({"os_wal", "user_action", "runtime_os"})
    DEFAULT_GROUND_THRESHOLD = 0.6

    def __init__(self, max_window: int = 300, ttl_cycles: int = 800):
        self.max_window = max_window
        self.ttl_cycles = ttl_cycles
        self.step_counter = 0

        self.frames: Dict[str, RealityFrame] = {}
        self.graph = nx.DiGraph()
        self._ordered_ids: deque[str] = deque()

        self._source_counter: Counter[str] = Counter()
        self._prev_entropy = 0.0
        self.entropy_rate = 0.0

        self._grounding_cache: Dict[str, float] = {}

    @property
    def stream(self) -> List[RealityFrame]:
        return self.get_reality_window(self.max_window)

    @property
    def valid_event_ids(self) -> Set[str]:
        return set(self._ordered_ids)

    # --- ingestion ---
    def ingest_os_events(self, events: List[Dict[str, Any]]) -> None:
        for raw in events:
            if not raw:
                continue
            payload = dict(raw.get("payload") or {})
            if "text" not in payload and raw.get("text"):
                payload["text"] = raw["text"]
            frame = RealityFrame(
                event_id=str(raw.get("event_id") or raw.get("id") or self._gen_id("os")),
                parent_id=raw.get("parent_id"),
                payload=payload,
                timestamp=float(raw.get("timestamp", time.time())),
                source=str(raw.get("source", "os_wal")),
            )
            self._add_frame(frame)

    def ingest_user_action(self, user_input: str, event_id: Optional[str] = None) -> str:
        eid = event_id or self._gen_id("user")
        frame = RealityFrame(
            event_id=eid,
            parent_id=None,
            payload={"type": "user_action", "content": user_input, "text": user_input},
            source="user_action",
        )
        self._add_frame(frame)
        return eid

    def ingest(self, frames: List[RealityFrame]) -> None:
        for frame in frames:
            self._add_frame(frame)

    def ingest_frame(self, frame: RealityFrame) -> str:
        self._add_frame(frame)
        return frame.event_id

    def _add_frame(self, frame: RealityFrame) -> None:
        self.frames[frame.event_id] = frame
        self.graph.add_node(
            frame.event_id,
            timestamp=frame.timestamp,
            source=frame.source,
        )

        if frame.parent_id and self.graph.has_node(frame.parent_id):
            self.graph.add_edge(frame.parent_id, frame.event_id)

        self._ordered_ids.append(frame.event_id)
        self._source_counter[frame.source] += 1
        self._grounding_cache.clear()

        self.step_counter += 1
        self._prune_old_nodes()
        self._recompute_entropy()

    def get_entropy_state(self) -> Tuple[float, float]:
        """Atomic entropy snapshot (H, ΔH) — piecewise dynamics across prune steps."""
        return self._prev_entropy, self.entropy_rate

    def batch_grounding_score(self, event_ids: List[str]) -> float:
        if not event_ids:
            return 0.0
        scores = [self.grounding_score(eid) for eid in event_ids]
        return sum(scores) / len(scores)

    def _recompute_entropy(self) -> None:
        if not self._source_counter:
            self._prev_entropy = 0.0
            self.entropy_rate = 0.0
            return

        total = sum(self._source_counter.values())
        probs = [count / total for count in self._source_counter.values()]
        entropy = -sum(p * math.log(p + 1e-12) for p in probs)
        self.entropy_rate = entropy - self._prev_entropy
        if abs(self.entropy_rate) < 1e-9:
            self.entropy_rate = 0.0
        self._prev_entropy = max(0.0, entropy)

    def _prune_old_nodes(self) -> None:
        """Causal-safe: prune oldest leaf only; sync source counter."""
        while len(self._ordered_ids) > self.max_window:
            old_id = self._ordered_ids[0]

            if not self.graph.has_node(old_id) or self.graph.out_degree(old_id) != 0:
                break

            source = self.frames.get(old_id, RealityFrame(old_id)).source
            self._ordered_ids.popleft()
            self.frames.pop(old_id, None)
            self.graph.remove_node(old_id)
            self._grounding_cache.pop(old_id, None)

            if source in self._source_counter:
                self._source_counter[source] -= 1
                if self._source_counter[source] <= 0:
                    del self._source_counter[source]

            self._recompute_entropy()

    # --- query ---
    def get_reality_window(self, n: int = 60) -> List[RealityFrame]:
        ids = list(self._ordered_ids)[-n:]
        return [self.frames[eid] for eid in ids if eid in self.frames]

    def window(self, n: int = 50) -> List[RealityFrame]:
        return self.get_reality_window(n)

    def grounding_score(self, event_id: str, *, decay: float = 0.88) -> float:
        if event_id not in self.graph:
            return 0.0

        if event_id in self._grounding_cache:
            return self._grounding_cache[event_id]

        source = self.graph.nodes[event_id].get("source", "unknown")
        base = 1.0 if source in self.GROUNDED_SOURCES else 0.3

        ancestors = nx.ancestors(self.graph, event_id)
        if not ancestors:
            score = base
        else:
            influence = 0.0
            for ancestor in ancestors:
                influence += decay ** self._path_distance(ancestor, event_id)
            score = min(1.0, base + influence / (len(ancestors) + 1))

        self._grounding_cache[event_id] = score
        return score

    def _path_distance(self, a: str, b: str) -> int:
        try:
            return nx.shortest_path_length(self.graph, a, b)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return 10

    def causal_ancestors(self, event_id: str) -> Set[str]:
        if not self.graph.has_node(event_id):
            return set()
        return set(nx.ancestors(self.graph, event_id))

    def is_grounded(
        self,
        ref: Optional[str],
        *,
        include_ancestors: bool = True,
        threshold: float = DEFAULT_GROUND_THRESHOLD,
    ) -> bool:
        if not ref:
            return False
        if self.grounding_score(ref) > threshold:
            return True
        if ref in self.valid_event_ids and self.grounding_score(ref) > 0.0:
            return self.grounding_score(ref) >= threshold * 0.5
        if include_ancestors:
            for eid in self.valid_event_ids:
                if ref in self.causal_ancestors(eid):
                    return self.grounding_score(ref) > 0.0 or ref in self.frames
        return ref in self.frames

    def entropy(self) -> float:
        return self._prev_entropy

    def consistency_check(self) -> bool:
        return set(self.frames.keys()) == set(self.graph.nodes)

    def get_latest_event_id(self) -> Optional[str]:
        return self._ordered_ids[-1] if self._ordered_ids else None

    def graph_stats(self) -> Dict[str, Any]:
        return {
            "stream_len": len(self._ordered_ids),
            "graph_nodes": self.graph.number_of_nodes(),
            "graph_edges": self.graph.number_of_edges(),
            "entropy": round(self.entropy(), 4),
            "entropy_rate": round(self.entropy_rate, 6),
            "entropy_dynamics": "piecewise",
            "consistent": self.consistency_check(),
            "step_counter": self.step_counter,
        }

    def _gen_id(self, prefix: str) -> str:
        return f"{prefix}_{int(time.time() * 1_000_000)}"
