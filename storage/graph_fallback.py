from datetime import datetime
from typing import Dict, List


class InMemoryCognitiveGraph:
    """Fallback cognitive graph when Kuzu is unavailable (e.g. Unicode paths on Windows)."""

    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Dict] = []

    def create_memory_node(self, memory_id: str, content: str, layer: str, importance: float):
        self.nodes[memory_id] = {
            "id": memory_id,
            "content": content[:2000],
            "layer": layer,
            "importance": importance,
            "created_at": datetime.now().isoformat(),
        }

    def link_memories(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        weight: float = 0.7,
        confidence: float = 0.8,
    ):
        self.edges.append(
            {
                "from": from_id,
                "to": to_id,
                "relation": relation,
                "weight": weight,
                "confidence": confidence,
            }
        )

    def find_related_memories(self, memory_id: str, max_hops: int = 2, limit: int = 20) -> List[Dict]:
        related = []
        for edge in self.edges:
            if edge["from"] == memory_id and edge["to"] in self.nodes:
                node = self.nodes[edge["to"]]
                related.append(
                    {
                        "id": node["id"],
                        "content": node["content"],
                        "hops": 1,
                        "path_weight": edge["weight"],
                    }
                )
        related.sort(key=lambda x: x["path_weight"], reverse=True)
        return related[:limit]

    def delete_memory_node(self, memory_id: str) -> bool:
        if memory_id not in self.nodes:
            return False
        del self.nodes[memory_id]
        self.edges = [
            e for e in self.edges if e["from"] != memory_id and e["to"] != memory_id
        ]
        return True

    def belief_conflict_scan(self):
        pass
