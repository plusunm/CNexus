from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Memory(BaseModel):
    memory_id: str = Field(..., description="唯一ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    role: str
    content: str
    layer: str = "episodic"
    importance: float = Field(0.5, ge=0.0, le=1.0)
    emotional_weight: float = Field(0.5, ge=0.0, le=1.0)
    salience_score: float = Field(0.5, ge=0.0, le=1.0)
    embedding: Optional[List[float]] = None
    semantic_summary: Optional[str] = None
    provenance: List[Dict] = Field(default_factory=list)
    confidence: float = Field(0.7, ge=0.0, le=1.0)
    decay_factor: float = 1.0
    related_memories: List[str] = Field(default_factory=list)
    metadata: Dict = Field(default_factory=dict)
    access_count: int = 1
    last_accessed_at: Optional[datetime] = None

    model_config = {"arbitrary_types_allowed": True}

    def model_dump_for_storage(self) -> dict:
        data = self.model_dump()
        data["created_at"] = self.timestamp.isoformat()
        if self.last_accessed_at:
            data["last_accessed_at"] = self.last_accessed_at.isoformat()
        else:
            data["last_accessed_at"] = self.timestamp.isoformat()
        return data
