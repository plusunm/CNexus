"""L3-G1 — constraint graph data model (descriptive topology only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConstraintType(str, Enum):
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    AUTHORITY = "authority"
    SAFETY = "safety"


@dataclass
class ConstraintNode:
    id: str
    type: ConstraintType
    weight: float
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "weight": round(self.weight, 4),
            "active": self.active,
        }


@dataclass
class ConstraintEdge:
    from_node: str
    to_node: str
    relation: str  # depends_on / overrides / conflicts
    strength: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": self.from_node,
            "to": self.to_node,
            "relation": self.relation,
            "strength": round(self.strength, 4),
        }


@dataclass
class ConstraintGraph:
    nodes: dict[str, ConstraintNode]
    edges: list[ConstraintEdge]

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
        }

    def summary(self) -> dict[str, int]:
        return {"nodes": len(self.nodes), "edges": len(self.edges)}
