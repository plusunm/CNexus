import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def _resolve_kuzu_db_path(db_path: str) -> Path:
    """Kuzu expects a database path, not a pre-created empty directory."""
    resolved = Path(db_path).expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    if resolved.is_dir() and not any(resolved.iterdir()):
        try:
            resolved.rmdir()
        except OSError:
            pass
    return resolved


def create_cognitive_graph(db_path: str = "memory/kuzu_db"):
    """Create Kuzu graph or fall back to in-memory graph on failure."""
    resolved = _resolve_kuzu_db_path(db_path)

    try:
        import kuzu

        db = kuzu.Database(str(resolved))
        conn = kuzu.Connection(db)
        graph = _KuzuCognitiveGraph(db, conn)
        graph._init_schema()
        return graph
    except Exception as exc:
        logger.warning("Kuzu unavailable (%s), using in-memory graph fallback", exc)
        from storage.graph_fallback import InMemoryCognitiveGraph

        return InMemoryCognitiveGraph()


class _KuzuCognitiveGraph:
    def __init__(self, db, conn):
        self.db = db
        self.conn = conn

    def _init_schema(self):
        self.conn.execute("""
            CREATE NODE TABLE IF NOT EXISTS MemoryNode (
                id STRING PRIMARY KEY,
                content STRING,
                layer STRING,
                importance FLOAT,
                created_at STRING,
                identity_anchor FLOAT DEFAULT 0.5
            )
        """)
        for rel in ["RELATES_TO", "SUPPORTS", "CONTRADICTS", "REINFORCES", "WEAKENS", "PART_OF"]:
            self.conn.execute(
                f"CREATE REL TABLE IF NOT EXISTS {rel} "
                f"(FROM MemoryNode TO MemoryNode, weight FLOAT, confidence FLOAT)"
            )

    def create_memory_node(self, memory_id: str, content: str, layer: str, importance: float):
        self.conn.execute(
            """
            CREATE (m:MemoryNode {id: $id, content: $content, layer: $layer,
                                 importance: $imp, created_at: $ts})
            """,
            {
                "id": memory_id,
                "content": content[:2000],
                "layer": layer,
                "imp": importance,
                "ts": datetime.now().isoformat(),
            },
        )

    def link_memories(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        weight: float = 0.7,
        confidence: float = 0.8,
    ):
        self.conn.execute(
            f"""
            MATCH (a:MemoryNode {{id: $from}}), (b:MemoryNode {{id: $to}})
            CREATE (a)-[r:{relation} {{weight: $w, confidence: $c}}]->(b)
            """,
            {"from": from_id, "to": to_id, "w": weight, "c": confidence},
        )

    def find_related_memories(self, memory_id: str, max_hops: int = 2, limit: int = 20) -> List[Dict]:
        result = self.conn.execute(
            f"""
            MATCH path = (m:MemoryNode {{id: $id}})-[*1..{max_hops}]->(n:MemoryNode)
            RETURN n.id as id, n.content as content, length(path) as hops,
                   reduce(w = 1.0, r in relationships(path) | w * r.weight) as path_weight
            ORDER BY path_weight DESC
            LIMIT $limit
            """,
            {"id": memory_id, "limit": limit},
        )
        rows = []
        while result.has_next():
            rows.append(result.get_next())
        return rows

    def delete_memory_node(self, memory_id: str) -> bool:
        try:
            self.conn.execute(
                "MATCH (m:MemoryNode {id: $id}) DETACH DELETE m",
                {"id": memory_id},
            )
            return True
        except Exception:
            return False

    def belief_conflict_scan(self):
        pass


# Backward-compatible alias
KuzuCognitiveGraph = create_cognitive_graph
