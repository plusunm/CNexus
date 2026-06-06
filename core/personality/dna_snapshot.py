from datetime import datetime
from typing import List, Optional

from core.personality.dna_schema import PersonalityDNA


class DNASnapshotManager:
    """DNA 快照管理 — 支持回滚"""

    def __init__(self):
        self.snapshots: List[PersonalityDNA] = []

    def create_snapshot(self, dna: PersonalityDNA):
        self.snapshots.append(dna.model_copy())
        if len(self.snapshots) > 50:
            self.snapshots.pop(0)

    def rollback(self, index: int = -1) -> Optional[PersonalityDNA]:
        if not self.snapshots:
            return None
        return self.snapshots[index]
