"""MemoryManager — L1 unified entry for all memory operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from memory.block import (
    BLOCK_SPECS,
    EPISODIC_TYPE_TO_LABEL,
    EpisodicMemoryBlock,
    MemoryBlock,
    create_episodic_block,
)
from memory.block_store import MemoryBlockStore
from memory.filter import CaptureFilter
from memory.governance_hook import BlockGovernanceHook, GovernanceResult
from memory.lifecycle import BlockLifecycleManager, MemoryManagementConfig
from memory.runtime_guard import RuntimeViolationError, assert_runtime_context

if TYPE_CHECKING:
    from core.governance.safety.write_gate import MemoryWriteGate
    from storage.manager import UnifiedStorageManager

# layer → MemoryBlock label routing for controlled block writes
LAYER_TO_BLOCK: Dict[str, str] = {
    "identity": "persona",
    "goal": "intent",
    "working": "working_memory",
    "relationship": "user_profile",
}

# Structured blocks owned by dedicated engines — no raw text dual-write on capture.
ENGINE_MANAGED_BLOCK_LABELS = frozenset({"intent"})


class MemoryManager:
    """
    L1 Memory Infrastructure — single entry point for memory operations.

    Block operations (structured state) go through Governance Hook → MemoryBlockStore.
    Episodic operations (interaction stream) delegate to UnifiedStorageManager.
    """

    def __init__(
        self,
        base_dir: str | Path,
        *,
        storage: Optional["UnifiedStorageManager"] = None,
        write_gate: Optional["MemoryWriteGate"] = None,
        bypass_runtime_guard: bool = False,
    ):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._bypass_runtime_guard = bypass_runtime_guard

        self.blocks = MemoryBlockStore(self.base_dir / "blocks")
        self.governance = BlockGovernanceHook(write_gate)
        self._last_gov: Optional[GovernanceResult] = None
        self.block_lifecycle = BlockLifecycleManager(MemoryManagementConfig())
        self._episodic_lifecycle = None

        if storage is not None:
            self.storage = storage
        else:
            from storage.manager import UnifiedStorageManager

            self.storage = UnifiedStorageManager(base_dir=str(self.base_dir))

    def set_write_gate(self, write_gate: "MemoryWriteGate") -> None:
        self.governance.write_gate = write_gate

    def _require_runtime_write(self, operation: str) -> None:
        if not self._bypass_runtime_guard:
            assert_runtime_context(operation)

    def set_embedder(self, embedder) -> None:
        self.storage.set_embedder(embedder)

    def configure_lifecycle(self, lifecycle_manager) -> None:
        self.storage.configure_lifecycle(lifecycle_manager)
        self._episodic_lifecycle = lifecycle_manager
        self.block_lifecycle = BlockLifecycleManager(lifecycle_manager.config)

    @staticmethod
    def resolve_block_label(
        layer: str,
        *,
        block_label: Optional[str] = None,
        meta: Optional[Dict] = None,
    ) -> Optional[str]:
        if block_label:
            return block_label
        if meta and meta.get("block_label"):
            return str(meta["block_label"])
        return LAYER_TO_BLOCK.get(layer)

    def _record_governance(self, gov: GovernanceResult, *, label: str, block_id: Optional[str] = None) -> None:
        self._last_gov = gov
        if gov.status == "flagged":
            self.blocks._append_provenance({
                "event": "governance_flagged",
                "label": label,
                "block_id": block_id,
                "status": gov.status,
                "consistency_flags": gov.consistency_flags,
            })

    def _write_block_for_label(
        self,
        label: str,
        content: str,
        *,
        importance: Optional[float] = None,
        source: str = "interaction",
        embedding: Optional[List[float]] = None,
    ) -> Union[MemoryBlock, Dict[str, str], None]:
        existing = self.blocks.get_active_by_label(label)
        if existing:
            result = self.update_block(
                existing.block_id,
                content,
                source=source,
                embedding=embedding,
            )
        else:
            result = self.create_block(
                label,
                content,
                importance=importance,
                source=source,
                embedding=embedding,
            )
        return result

    # ── Block CRUD (structured memory) ─────────────────────────────────

    def create_block(
        self,
        label: str,
        content: str,
        *,
        description: str = "",
        importance: Optional[float] = None,
        source: str = "interaction",
        tags: Optional[List[str]] = None,
        embedding: Optional[List[float]] = None,
    ) -> Union[MemoryBlock, Dict[str, str]]:
        self._require_runtime_write("create_block")
        if label not in BLOCK_SPECS:
            return {"error": f"unknown label: {label}"}

        spec_importance = float(
            importance if importance is not None else BLOCK_SPECS[label].get("importance", 0.5)
        )
        gov = self.governance.check(label, content, spec_importance)
        if not gov.allowed:
            self._last_gov = gov
            return {"denied": gov.reason, "risk": gov.risk_score}

        block = MemoryBlock.from_label(
            label,
            content[: BLOCK_SPECS[label]["limit"]],
            description=description,
            importance=spec_importance,
            source=source,
            tags=tags,
            governance_status=gov.status,
            consistency_flags=gov.consistency_flags,
        )
        if embedding is not None:
            block.embedding = embedding
        elif self.storage._embedder:
            block.embedding = self.storage._get_embedding(block.content)

        created = self.blocks.create(block)
        self._record_governance(gov, label=label, block_id=created.block_id)
        return created

    def get_block(self, block_id: str) -> Optional[MemoryBlock]:
        return self.blocks.get(block_id)

    def get_active_block(self, label: str, *, touch: bool = True) -> Optional[MemoryBlock]:
        block = self.blocks.get_active_by_label(label)
        if block and touch:
            return self.blocks.touch_access(block.block_id)
        return block

    def update_block(
        self,
        block_id: str,
        content: str,
        *,
        source: str = "interaction",
        tags: Optional[List[str]] = None,
        embedding: Optional[List[float]] = None,
    ) -> Union[MemoryBlock, Dict[str, str], None]:
        self._require_runtime_write("update_block")
        current = self.blocks.get(block_id)
        if not current:
            return None

        gov = self.governance.check(
            current.label,
            content,
            current.importance,
            existing_content=current.content,
        )
        if not gov.allowed:
            self._last_gov = gov
            return {"denied": gov.reason, "risk": gov.risk_score}

        if embedding is None and self.storage._embedder:
            embedding = self.storage._get_embedding(content)

        updated = self.blocks.update(
            block_id,
            content=content,
            source=source,
            tags=tags,
            governance_status=gov.status,
            consistency_flags=gov.consistency_flags,
            embedding=embedding,
        )
        self._record_governance(gov, label=current.label, block_id=block_id)
        return updated

    def delete_block(self, block_id: str) -> bool:
        self._require_runtime_write("delete_block")
        return self.blocks.delete(block_id)

    def list_blocks(
        self,
        *,
        label: Optional[str] = None,
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> List[MemoryBlock]:
        return self.blocks.list_blocks(
            label=label, category=category, active_only=active_only
        )

    def get_version_history(self, block_id: str) -> List[MemoryBlock]:
        return self.blocks.get_version_history(block_id)

    def get_core_context_blocks(self) -> List[MemoryBlock]:
        """Return active core blocks sorted by recall priority."""
        from memory.block import LABEL_PRIORITY

        blocks = self.blocks.list_core_blocks()
        blocks.sort(key=lambda b: LABEL_PRIORITY.get(b.label, 0.0), reverse=True)
        return blocks

    def recall_blocks(self, query: str = "", labels: Optional[List[str]] = None) -> List[MemoryBlock]:
        """Return active blocks for recall, optionally filtered by label list."""
        from memory.block import LABEL_PRIORITY

        if labels:
            selected = labels
        else:
            selected = sorted(LABEL_PRIORITY.keys(), key=lambda lb: LABEL_PRIORITY[lb], reverse=True)

        results: List[MemoryBlock] = []
        for label in selected:
            block = self.get_active_block(label, touch=True)
            if block:
                results.append(block)
        return results

    # ── Block lifecycle maintenance ──────────────────────────────────────

    def protect_block(self, label: str) -> Optional[MemoryBlock]:
        block = self.blocks.get_active_by_label(label)
        if not block:
            return None
        block.protected = True
        return self.blocks.save(block)

    def compress_archival_blocks(self) -> Dict:
        all_blocks = self.blocks.get_all_blocks(active_only=True)
        updated, count = self.block_lifecycle.compress_archival(all_blocks)
        archival_ids = {b.block_id for b in updated if b.label == "archival_facts" and b.active}

        for block in all_blocks:
            if block.label == "archival_facts" and block.block_id not in archival_ids:
                self.blocks.delete(block.block_id)

        for block in updated:
            if block.label == "archival_facts" and block.active:
                self.blocks.save(block)

        return {"compressed": count, "remaining_archival": len(archival_ids)}

    def run_maintenance(self, *, force: bool = False) -> Dict:
        """Run block lifecycle maintenance + episodic maintenance."""
        all_blocks = self.blocks.get_all_blocks(active_only=True)
        before_ids = {b.block_id for b in all_blocks}

        maintained, block_report = self.block_lifecycle.run_block_maintenance(all_blocks)
        maintained_ids = {b.block_id for b in maintained}

        for block in maintained:
            self.blocks.save(block)

        for bid in before_ids - maintained_ids:
            self.blocks.delete(bid)

        episodic_report: Dict = {"skipped": True}
        if self._episodic_lifecycle is not None:
            episodic_report = self._episodic_lifecycle.run_maintenance(force=force).to_dict()

        return {
            "blocks": block_report.to_dict(),
            "episodic": episodic_report,
        }

    # ── Unified capture (episodic trace + optional block routing) ────────

    def capture_interaction(
        self,
        role: str,
        content: str,
        *,
        layer: str = "episodic",
        importance: float = 0.5,
        emotional_weight: float = 0.5,
        embedding: Optional[List[float]] = None,
        block_label: Optional[str] = None,
        source: str = "interaction",
        **meta,
    ) -> Dict:
        """
        Dual-write capture: episodic trace (always) + MemoryBlock (when routed).

        Episodic write assumes upstream WriteGate approval (runtime.capture).
        Block write runs BlockGovernanceHook (approved / flagged / rejected).
        """
        self._require_runtime_write("capture_interaction")
        storage_meta = dict(meta)
        storage_meta.pop("block_label", None)
        storage_meta.pop("return_detail", None)

        if embedding is None and self.storage._embedder:
            embedding = self.storage._get_embedding(content)

        episodic_id = self.storage.capture_memory(
            role=role,
            content=content,
            layer=layer,
            importance=importance,
            emotional_weight=emotional_weight,
            embedding=embedding,
            **storage_meta,
        )

        resolved_label = self.resolve_block_label(
            layer, block_label=block_label, meta=meta
        )
        block_result: Optional[Union[MemoryBlock, Dict]] = None
        governance_info: Optional[Dict] = None

        if resolved_label and (
            resolved_label not in ENGINE_MANAGED_BLOCK_LABELS
            or meta.get("force_block_write")
        ):
            block_result = self._write_block_for_label(
                resolved_label,
                content,
                importance=importance,
                source=source,
                embedding=embedding,
            )
            if self._last_gov:
                governance_info = {
                    "label": resolved_label,
                    "status": self._last_gov.status,
                    "consistency_flags": self._last_gov.consistency_flags,
                    "risk_score": self._last_gov.risk_score,
                }

        return {
            "episodic_id": episodic_id,
            "block_label": resolved_label,
            "block": block_result,
            "governance": governance_info,
            "episodic_block": self._mirror_episodic_block(
                role=role,
                content=content,
                layer=layer,
                episodic_id=episodic_id,
                importance=importance,
                meta=meta,
            ),
        }

    def _mirror_episodic_block(
        self,
        *,
        role: str,
        content: str,
        layer: str,
        episodic_id: str,
        importance: float,
        meta: Dict,
    ) -> Optional[MemoryBlock]:
        """Write typed episodic block entries alongside vector/graph capture."""
        episodic_type = str(meta.get("episodic_type") or self._infer_episodic_type(layer, role))
        label = EPISODIC_TYPE_TO_LABEL.get(episodic_type, "episodic_dialogue")
        block = self.get_active_block(label, touch=False)
        if block is None:
            block = create_episodic_block(episodic_type)
            block = self.blocks.create(block)
        if not isinstance(block, EpisodicMemoryBlock):
            return block
        block.add_structured_entry(
            {
                "role": role,
                "content": content,
                "layer": layer,
                "importance": importance,
                "episodic_id": episodic_id,
                "episodic_type": episodic_type,
            }
        )
        if episodic_type == "dialogue" and episodic_id:
            self.link_episodic_chain(dialogue_id=episodic_id)
        if meta.get("graph_node_id"):
            block.graph_node_id = str(meta["graph_node_id"])
        if meta.get("embedding_ref"):
            block.embedding_ref = str(meta["embedding_ref"])
        else:
            block.embedding_ref = episodic_id
        return self.blocks.save(block)

    def link_episodic_chain(
        self,
        *,
        event_id: Optional[str] = None,
        dialogue_id: Optional[str] = None,
        decision_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Link episodic vector ids in Kuzu + annotate typed block entries."""
        links = self.storage.link_episodic_chain(
            event_id=event_id,
            dialogue_id=dialogue_id,
            decision_id=decision_id,
        )
        for episodic_type, episodic_id in (
            ("event", event_id),
            ("dialogue", dialogue_id),
            ("decision", decision_id),
        ):
            if not episodic_id:
                continue
            block = self.get_active_block(
                EPISODIC_TYPE_TO_LABEL.get(episodic_type, "episodic_dialogue"),
                touch=False,
            )
            if isinstance(block, EpisodicMemoryBlock):
                block.metadata["graph_links"] = links
                self.blocks.save(block)
        return links

    def get_attention_state_block(self):
        from memory.block import AttentionStateBlock

        block = self.get_active_block("attention_state", touch=False)
        return block if isinstance(block, AttentionStateBlock) else block

    def get_episodic_block(self, episodic_type: str):
        label = EPISODIC_TYPE_TO_LABEL.get(episodic_type, "episodic_dialogue")
        return self.get_active_block(label, touch=False)

    def recall_episodic_typed(
        self,
        episodic_type: Optional[str] = None,
        *,
        limit: int = 5,
    ) -> List[MemoryBlock]:
        if episodic_type:
            block = self.get_episodic_block(episodic_type)
            return [block] if block else []
        blocks = self.blocks.list_episodic_blocks()
        return blocks[:limit]

    @staticmethod
    def _infer_episodic_type(layer: str, role: str) -> str:
        if layer in {"decision", "decision_trace"}:
            return "decision"
        if layer in {"event", "event_graph"}:
            return "event"
        if role in {"system", "assistant", "user"} or layer in {"episodic", "dialogue", "dialogue_trace"}:
            return "dialogue"
        return "dialogue"

    def append_episodic_entry(
        self,
        episodic_type: str,
        entry: Dict,
        *,
        episodic_id: Optional[str] = None,
    ) -> MemoryBlock:
        label = EPISODIC_TYPE_TO_LABEL.get(episodic_type, "episodic_dialogue")
        block = self.get_active_block(label, touch=False)
        if block is None:
            block = self.blocks.create(create_episodic_block(episodic_type))
        if isinstance(block, EpisodicMemoryBlock):
            payload = dict(entry)
            if episodic_id:
                payload["episodic_id"] = episodic_id
            block.add_structured_entry(payload)
            if episodic_id:
                block.embedding_ref = episodic_id
            return self.blocks.save(block)
        return block

    def sync_attention_block(
        self,
        focus_scores: Dict[str, float],
        top_focus: List[str],
        turn: int,
    ) -> MemoryBlock:
        return self.blocks.sync_attention_from_dynamic(focus_scores, top_focus, turn)

    def get_attention_snapshot(self) -> Dict:
        block = self.blocks.get_attention_snapshot()
        if block is None:
            return {}
        return block.read_snapshot()

    def get_attention_state(self, user_id: Optional[str] = None):
        return self.blocks.get_attention_state(user_id)

    def add_episodic_triple(
        self,
        event: Dict,
        dialogue: Dict,
        decision: Dict,
        *,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        link: bool = True,
    ) -> Dict[str, str]:
        return self.blocks.add_episodic_triple(
            event,
            dialogue,
            decision,
            user_id=user_id,
            session_id=session_id,
            link=link,
        )

    # ── Episodic pass-through (interaction stream) ─────────────────────

    def capture_memory(
        self,
        role: str,
        content: str,
        layer: str = "episodic",
        importance: float = 0.5,
        emotional_weight: float = 0.5,
        **meta,
    ) -> str:
        self._require_runtime_write("capture_memory")
        return self.storage.capture_memory(
            role=role,
            content=content,
            layer=layer,
            importance=importance,
            emotional_weight=emotional_weight,
            **meta,
        )

    def recall(
        self,
        query: str,
        top_k: int = 12,
        layer: Optional[str] = None,
        min_importance: float = 0.0,
    ) -> List[Dict]:
        return self.storage.recall(
            query=query,
            top_k=top_k,
            layer=layer,
            min_importance=min_importance,
        )

    def capture_with_filter(
        self,
        role: str,
        content: str,
        layer: str = "episodic",
        importance: float = 0.5,
        emotional_weight: float = 0.5,
        **meta,
    ) -> Union[str, Dict[str, str]]:
        rejected, reason = CaptureFilter.should_reject(role, content)
        if rejected:
            return {"denied": reason}
        return self.capture_memory(
            role, content, layer, importance, emotional_weight, **meta
        )

    # ── Introspection ──────────────────────────────────────────────────

    def block_stats(self) -> Dict:
        all_blocks = self.blocks.list_blocks(active_only=True)
        by_label: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        for b in all_blocks:
            by_label[b.label] = by_label.get(b.label, 0) + 1
            by_category[b.category] = by_category.get(b.category, 0) + 1
        return {
            "total_active": len(all_blocks),
            "by_label": by_label,
            "by_category": by_category,
            "known_labels": self.blocks.known_labels(),
        }

    def last_governance_result(self) -> Optional[GovernanceResult]:
        return self._last_gov or self.governance.last_result
