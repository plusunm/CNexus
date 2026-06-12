import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.personality.belief.belief_schema import Belief, BeliefGraph
from core.personality.dna_engine import PersonalityDNAEngine
from core.personality.narrative.narrative_builder import NarrativeBuilder

BELIEF_STORE_LABEL = "belief_store"
NARRATIVE_LABEL = "narrative"


class BeliefEngine:
    """Belief Governance Engine — in-memory graph + belief_store block persistence."""

    def __init__(
        self,
        dna_engine: PersonalityDNAEngine,
        narrative_builder: NarrativeBuilder,
        *,
        memory_manager=None,
    ):
        self.dna = dna_engine
        self.narrative = narrative_builder
        self.graph = BeliefGraph()
        self._memory_manager = memory_manager

    def set_memory_manager(self, memory_manager) -> None:
        self._memory_manager = memory_manager

    def add_or_update_belief(
        self, content: str, confidence: float = 0.75, source_memory_id: str = None
    ) -> str:
        belief_id = f"belief_{hash(content) % 10000000:07d}"

        if belief_id in self.graph.beliefs:
            existing = self.graph.beliefs[belief_id]
            existing.confidence = min(1.0, (existing.confidence + confidence) / 1.6)
            existing.evidence_count += 1
        else:
            belief = Belief(
                belief_id=belief_id,
                content=content,
                confidence=confidence,
                source_memory_id=source_memory_id,
            )
            self.graph.add_belief(belief)

        if confidence > 0.8:
            self.narrative.update_from_memory(f"Belief reinforced: {content}", importance=confidence)
            self._persist_narrative_block()

        self._persist_belief_block()
        return belief_id

    def _persist_belief_block(self) -> None:
        if self._memory_manager is None:
            return
        payload = self.export_belief_store_payload()
        content = json.dumps(payload, ensure_ascii=False)
        existing = self._memory_manager.get_active_block(BELIEF_STORE_LABEL, touch=False)
        if existing:
            self._memory_manager.update_block(
                existing.block_id,
                content,
                source="belief_engine",
            )
        else:
            self._memory_manager.create_block(
                BELIEF_STORE_LABEL,
                content,
                source="belief_engine",
            )

    def _persist_narrative_block(self) -> None:
        if self._memory_manager is None:
            return
        summary = self.narrative.get_current_narrative_summary()
        if not summary:
            return
        payload = {
            "summary": summary,
            "coherence": self.narrative.narrative.narrative_coherence_score,
            "updated_at": datetime.now().isoformat(),
        }
        content = json.dumps(payload, ensure_ascii=False)
        existing = self._memory_manager.get_active_block(NARRATIVE_LABEL, touch=False)
        if existing:
            self._memory_manager.update_block(
                existing.block_id,
                content,
                source="belief_engine",
            )
        else:
            self._memory_manager.create_block(
                NARRATIVE_LABEL,
                content,
                source="belief_engine",
            )

    def export_belief_store_payload(self) -> Dict:
        beliefs = {}
        for bid, belief in self.graph.beliefs.items():
            beliefs[bid] = {
                "content": belief.content,
                "confidence": belief.confidence,
                "evidence_count": belief.evidence_count,
                "source_memory_id": belief.source_memory_id,
                "last_verified": belief.last_verified.isoformat(),
            }
        return {
            "beliefs": beliefs,
            "updated_at": datetime.now().isoformat(),
            "count": len(beliefs),
        }

    def hydrate_from_block(self, content: str) -> int:
        """Load beliefs from belief_store block JSON. Returns count loaded."""
        if not content or not str(content).strip().startswith("{"):
            return 0
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return 0
        beliefs = payload.get("beliefs") or {}
        loaded = 0
        for bid, data in beliefs.items():
            if bid in self.graph.beliefs:
                continue
            self.graph.beliefs[bid] = Belief(
                belief_id=bid,
                content=data.get("content", ""),
                confidence=float(data.get("confidence", 0.5)),
                source_memory_id=data.get("source_memory_id"),
            )
            loaded += 1
        return loaded

    def restore_from_memory_manager(self) -> Tuple[int, int]:
        """Restart recovery — belief_store + narrative blocks."""
        belief_count = 0
        narrative_count = 0
        if self._memory_manager is None:
            return belief_count, narrative_count
        belief_block = self._memory_manager.get_active_block(BELIEF_STORE_LABEL, touch=False)
        if belief_block:
            belief_count = self.hydrate_from_block(belief_block.content)
        narrative_block = self._memory_manager.get_active_block(NARRATIVE_LABEL, touch=False)
        if narrative_block and narrative_block.content.strip().startswith("{"):
            try:
                payload = json.loads(narrative_block.content)
                summary = payload.get("summary")
                if summary:
                    self.narrative.narrative.identity_summary = summary[:500]
                    narrative_count = 1
            except json.JSONDecodeError:
                pass
        return belief_count, narrative_count

    def decay_confidence(self):
        now = datetime.now()
        for belief in self.graph.beliefs.values():
            days = (now - belief.last_verified).days
            if days > 7:
                decay = 0.98 ** (days - 7)
                belief.confidence *= decay
        self._persist_belief_block()

    def get_active_beliefs(self, min_confidence: float = 0.6) -> Dict[str, Belief]:
        return {k: v for k, v in self.graph.beliefs.items() if v.confidence >= min_confidence}
