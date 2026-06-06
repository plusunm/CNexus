from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import uuid

from memory.schema import Memory
from storage.graph import create_cognitive_graph
from storage.provenance import ProvenanceTracker
from storage.vector import LanceMemoryStore


class UnifiedStorageManager:
    def __init__(self, base_dir: str = "memory", vector_dim: int = 768):
        Path(base_dir).mkdir(parents=True, exist_ok=True)
        self.vector_dim = vector_dim
        self.vector = LanceMemoryStore(db_path=f"{base_dir}/lancedb")
        self.graph = create_cognitive_graph(db_path=f"{base_dir}/kuzu_db")
        self.provenance = ProvenanceTracker()
        self._embedder = None

    def set_embedder(self, embedder):
        self._embedder = embedder

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
                self.vector.update_memory(
                    mid,
                    {
                        "access_count": int(r.get("access_count", 0)) + 1,
                        "last_accessed_at": now,
                    },
                )
                r["access_count"] = int(r.get("access_count", 0)) + 1

        return results

    def promote_memory(self, memory_id: str, new_layer: str):
        self.vector.update_memory(memory_id, {"layer": new_layer})

    def forget_memory(self, memory_id: str):
        self.vector.delete_memory(memory_id)
