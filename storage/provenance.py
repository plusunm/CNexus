from datetime import datetime
from typing import Dict, List


class ProvenanceTracker:
    def __init__(self):
        self.records: Dict[str, List[Dict]] = {}

    def record_creation(self, memory_id: str, source_type: str, created_by: str):
        if memory_id not in self.records:
            self.records[memory_id] = []
        self.records[memory_id].append(
            {
                "timestamp": datetime.now().isoformat(),
                "source_type": source_type,
                "created_by": created_by,
                "version": 1,
            }
        )

    def get_provenance(self, memory_id: str) -> List[Dict]:
        return self.records.get(memory_id, [])
