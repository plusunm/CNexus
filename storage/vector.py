import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import lancedb
import numpy as np

from memory.schema import Memory


def _memory_to_row(memory: Memory) -> dict:
    """Flatten memory for LanceDB (avoid nested dict columns)."""
    return {
        "memory_id": memory.memory_id,
        "role": memory.role,
        "content": memory.content,
        "layer": memory.layer,
        "importance": float(memory.importance),
        "emotional_weight": float(memory.emotional_weight),
        "salience_score": float(memory.salience_score),
        "confidence": float(memory.confidence),
        "decay_factor": float(memory.decay_factor),
        "access_count": int(memory.access_count),
        "created_at": memory.timestamp.isoformat(),
        "last_accessed_at": (memory.last_accessed_at or memory.timestamp).isoformat(),
        "embedding": memory.embedding or [0.0] * 768,
    }


class LanceMemoryStore:
    def __init__(self, db_path: str = "memory/lancedb", table_name: str = "cognitive_memory"):
        Path(db_path).mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(db_path)
        self.table_name = table_name
        self._init_table()

    def _init_table(self):
        try:
            self.table = self.db.open_table(self.table_name)
            return
        except Exception:
            pass

        sample = _memory_to_row(
            Memory(
                memory_id=str(uuid.uuid4()),
                role="system",
                content="init placeholder record",
                layer="episodic",
                importance=0.0,
                embedding=[0.0] * 768,
            )
        )
        try:
            self.table = self.db.create_table(self.table_name, data=[sample])
        except ValueError as exc:
            if "already exists" in str(exc).lower():
                self.table = self.db.open_table(self.table_name)
            else:
                raise

    def insert_memory(self, memory: Memory) -> str:
        self.table.add([_memory_to_row(memory)])
        return memory.memory_id

    def search_memory(
        self,
        query_embedding: List[float],
        top_k: int = 12,
        min_importance: float = 0.0,
        layer: Optional[str] = None,
    ) -> List[Dict]:
        if self.table.count_rows() == 0:
            return []

        query = self.table.search(query_embedding)
        if layer:
            query = query.where(f"layer = '{layer}'")
        if min_importance > 0:
            query = query.where(f"importance >= {min_importance}")

        results = query.limit(top_k * 4).to_list()

        now = datetime.now()
        scored = []
        for r in results:
            created = r.get("created_at", now.isoformat())
            if isinstance(created, str):
                try:
                    age_hours = (now - datetime.fromisoformat(created)).total_seconds() / 3600
                except ValueError:
                    age_hours = 0
            else:
                age_hours = 0
            time_decay = max(0.1, float(np.exp(-age_hours / 96)))
            attention_boost = r.get("access_count", 1) * 0.1

            score = (
                (1 - r.get("_distance", 0.5)) * 0.45
                + r.get("importance", 0.5) * 0.25
                + r.get("emotional_weight", 0.5) * 0.15
                + time_decay * 0.10
                + attention_boost * 0.05
            )
            r["_hybrid_score"] = score
            scored.append(r)

        scored.sort(key=lambda x: x["_hybrid_score"], reverse=True)
        return scored[:top_k]

    def update_memory(self, memory_id: str, updates: Dict[str, Any]):
        self.table.update(where=f"memory_id = '{memory_id}'", values=updates)

    def delete_memory(self, memory_id: str):
        self.table.delete(f"memory_id = '{memory_id}'")
