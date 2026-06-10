from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

import uuid

from memory.schema import Memory
from storage.graph import create_cognitive_graph
from storage.provenance import ProvenanceTracker
from storage.vector import LanceMemoryStore

if TYPE_CHECKING:
    from memory.lifecycle import MaintenanceReport, MemoryStats


class UnifiedStorageManager:
    def __init__(self, base_dir: str = "memory", vector_dim: int = 768):
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        self.vector_dim = vector_dim
        self.vector = LanceMemoryStore(db_path=f"{base_dir}/lancedb")
        self.graph = create_cognitive_graph(db_path=f"{base_dir}/kuzu_db")
        self.provenance = ProvenanceTracker()
        self._embedder = None
        self._lifecycle = None
        self._recall_access_cap = 50

    def set_embedder(self, embedder):
        self._embedder = embedder

    def configure_lifecycle(self, lifecycle_manager) -> None:
        self._lifecycle = lifecycle_manager

    def set_recall_access_cap(self, cap: int) -> None:
        self._recall_access_cap = max(1, int(cap))

    def _get_embedding(self, text: str) -> List[float]:
        if self._embedder:
            return self._embedder.embed(text)
        return [0.0] * self.vector_dim

    def capture_memory(
        self,
        role: str,
        content: str,
        layer: str = "episodic",
        importance: float = 0.5,
        emotional_weight: float = 0.5,
        embedding: Optional[List[float]] = None,
        **meta,
    ) -> str:
        memory_id = str(uuid.uuid4())
        now = datetime.now()
        decay_factor = float(meta.pop("decay_factor", 1.0))

        memory = Memory(
            memory_id=memory_id,
            role=role,
            content=content,
            layer=layer,
            importance=importance,
            emotional_weight=emotional_weight,
            timestamp=now,
            last_accessed_at=now,
            access_count=1,
            decay_factor=decay_factor,
            embedding=embedding or self._get_embedding(content),
            metadata=meta,
        )

        self.vector.insert_memory(memory)
        self.graph.create_memory_node(memory_id, content, layer, importance)
        self.provenance.record_creation(memory_id, source_type="capture", created_by=role)

        return memory_id

    def recall(
        self,
        query: str,
        top_k: int = 12,
        layer: Optional[str] = None,
        min_importance: float = 0.0,
    ) -> List[Dict]:
        if not query or not query.strip():
            return []

        embedding = self._get_embedding(query.strip())
        results = self.vector.search_memory(
            embedding, top_k=top_k, layer=layer, min_importance=min_importance
        )

        now = datetime.now().isoformat()
        for r in results:
            mid = r.get("memory_id")
            if mid:
                new_count = min(
                    self._recall_access_cap,
                    int(r.get("access_count", 0)) + 1,
                )
                self.vector.update_memory(
                    mid,
                    {
                        "access_count": new_count,
                        "last_accessed_at": now,
                    },
                )
                r["access_count"] = new_count

        return results

    def promote_memory(self, memory_id: str, new_layer: str):
        self.vector.update_memory(memory_id, {"layer": new_layer})

    def forget_memory(self, memory_id: str):
        self.vector.delete_memory(memory_id)
        if hasattr(self.graph, "delete_memory_node"):
            self.graph.delete_memory_node(memory_id)

    def memory_stats(self) -> "MemoryStats":
        if self._lifecycle is None:
            from memory.lifecycle import MemoryLifecycleManager, MemoryManagementConfig

            self._lifecycle = MemoryLifecycleManager(self, MemoryManagementConfig())
        return self._lifecycle.collect_stats()

    def run_memory_maintenance(self, *, force: bool = False) -> "MaintenanceReport":
        if self._lifecycle is None:
            from memory.lifecycle import MemoryLifecycleManager, MemoryManagementConfig

            self._lifecycle = MemoryLifecycleManager(self, MemoryManagementConfig())
        return self._lifecycle.run_maintenance(force=force)
