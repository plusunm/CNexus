import json
from pathlib import Path
from typing import List, Optional

from core.personality.reflective.reflective_memory import ReflectionRecord


class ReflectiveMemoryStore:
    """反思记录持久化 — 与向量存储解耦"""

    def __init__(self, base_dir: str = "memory"):
        self.path = Path(base_dir) / "reflective" / "records.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.records: List[ReflectionRecord] = []
        self.load()

    def load(self):
        if not self.path.exists():
            return
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.records = [ReflectionRecord(**r) for r in data.get("records", [])]

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                {"records": [r.model_dump(mode="json") for r in self.records]},
                f,
                indent=2,
                ensure_ascii=False,
            )

    def append(self, record: ReflectionRecord) -> ReflectionRecord:
        self.records.append(record)
        self.save()
        return record

    def get_active(self) -> List[ReflectionRecord]:
        return [r for r in self.records if r.status == "active"]

    def get(self, reflection_id: str) -> Optional[ReflectionRecord]:
        for r in self.records:
            if r.reflection_id == reflection_id:
                return r
        return None

    def update_status(self, reflection_id: str, status: str):
        for r in self.records:
            if r.reflection_id == reflection_id:
                r.status = status
                self.save()
                break
