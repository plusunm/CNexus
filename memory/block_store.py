"""CNexus L1 MemoryBlockStore — Option 2 (Episodic + Attention hybrid).

File-backed persistence (block_id + version history + provenance JSONL).
Label-based convenience API aligned with Letta/MemGPT block semantics.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from memory.block import (
    ARCHIVAL_LABELS,
    BLOCK_SPECS,
    BlockCategory,
    CORE_LABELS,
    EPISODIC_LABELS,
    AttentionStateBlock,
    EpisodicMemoryBlock,
    MemoryBlock,
    PROFILE_LABELS,
    SINGLETON_LABELS,
    create_block_from_spec,
)


def _content_to_str(content: Any) -> str:
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


class MemoryBlockStore:
    """Unified Memory Block storage — CRUD, recall, lifecycle, governance helpers."""

    def __init__(self, blocks_dir: str | Path):
        self.blocks_dir = Path(blocks_dir)
        self.blocks_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir = self.blocks_dir / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.blocks_dir / "index.json"
        self.provenance_path = self.blocks_dir / "provenance.jsonl"
        self._index: Dict[str, dict] = self._load_index()
        self._episodic_index: Dict[str, List[str]] = {
            "event": [],
            "dialogue": [],
            "decision": [],
        }
        self._attention_snapshot: Optional[AttentionStateBlock] = None
        self._rebuild_aux_indexes()

    # ── persistence helpers ──────────────────────────────────────────

    def _load_index(self) -> Dict[str, dict]:
        if not self.index_path.exists():
            return {}
        with open(self.index_path, encoding="utf-8") as fh:
            return json.load(fh)

    def _save_index(self) -> None:
        with open(self.index_path, "w", encoding="utf-8") as fh:
            json.dump(self._index, fh, ensure_ascii=False, indent=2)

    def _block_path(self, block_id: str) -> Path:
        return self.blocks_dir / f"{block_id}.json"

    def _version_path(self, block_id: str, version: int) -> Path:
        block_versions = self.versions_dir / block_id
        block_versions.mkdir(parents=True, exist_ok=True)
        return block_versions / f"v{version}.json"

    def _write_block(self, block: MemoryBlock) -> None:
        with open(self._block_path(block.block_id), "w", encoding="utf-8") as fh:
            json.dump(block.model_dump_for_storage(), fh, ensure_ascii=False, indent=2)

    def _read_block(self, block_id: str) -> Optional[MemoryBlock]:
        path = self._block_path(block_id)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as fh:
            return MemoryBlock.from_storage(json.load(fh))

    def _append_provenance(self, event: dict) -> None:
        event["timestamp"] = datetime.now().isoformat()
        with open(self.provenance_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _register(self, block: MemoryBlock) -> None:
        self._index[block.block_id] = {
            "block_id": block.block_id,
            "label": block.label,
            "version": block.version,
            "category": block.category,
            "active": block.active,
            "importance": block.importance,
            "updated_at": block.updated_at.isoformat(),
        }
        self._save_index()
        self._track_aux_indexes(block)

    def _rebuild_aux_indexes(self) -> None:
        self._episodic_index = {"event": [], "dialogue": [], "decision": []}
        self._attention_snapshot = None
        for entry in self._index.values():
            if not entry.get("active", True):
                continue
            block = self._read_block(entry["block_id"])
            if block:
                self._track_aux_indexes(block, rebuild=True)

    def _track_aux_indexes(self, block: MemoryBlock, *, rebuild: bool = False) -> None:
        if isinstance(block, EpisodicMemoryBlock):
            bucket = self._episodic_index.setdefault(block.episodic_type, [])
            if block.block_id not in bucket:
                bucket.append(block.block_id)
            elif not rebuild:
                return
        if isinstance(block, AttentionStateBlock) and block.active:
            self._attention_snapshot = block

    def _untrack_aux_indexes(self, block: MemoryBlock) -> None:
        if isinstance(block, EpisodicMemoryBlock):
            bucket = self._episodic_index.get(block.episodic_type, [])
            if block.block_id in bucket:
                bucket.remove(block.block_id)
        if isinstance(block, AttentionStateBlock) and self._attention_snapshot is block:
            self._attention_snapshot = None

    # ── Core CRUD (block_id API) ─────────────────────────────────────

    def create(
        self,
        block: MemoryBlock,
        *,
        allow_singleton_replace: bool = True,
    ) -> MemoryBlock:
        if block.label not in BLOCK_SPECS:
            raise ValueError(f"unknown block label: {block.label}")

        if block.label in SINGLETON_LABELS and allow_singleton_replace:
            existing = self.get_active_by_label(block.label)
            if existing:
                return self.update(
                    existing.block_id,
                    content=block.content,
                    source=block.source,
                    tags=block.tags,
                    governance_status=block.governance_status,
                    consistency_flags=block.consistency_flags,
                    embedding=block.embedding,
                )

        block.updated_at = datetime.now()
        self._write_block(block)
        self._register(block)
        self._append_provenance({
            "event": "create",
            "block_id": block.block_id,
            "label": block.label,
            "version": block.version,
            "source": block.source,
        })
        return block

    def get(self, block_id: str) -> Optional[MemoryBlock]:
        return self._read_block(block_id)

    def save(self, block: MemoryBlock) -> MemoryBlock:
        block.updated_at = datetime.now()
        self._write_block(block)
        self._register(block)
        return block

    def touch_access(self, block_id: str) -> Optional[MemoryBlock]:
        block = self._read_block(block_id)
        if not block or not block.active:
            return None
        block.touch()
        return self.save(block)

    def get_all_blocks(self, *, active_only: bool = True) -> List[MemoryBlock]:
        return self.list_blocks(active_only=active_only)

    def get_active_by_label(self, label: str, *, touch: bool = False) -> Optional[MemoryBlock]:
        for entry in self._index.values():
            if entry.get("label") == label and entry.get("active", True):
                block = self._read_block(entry["block_id"])
                if block and touch:
                    block.touch()
                    return self.save(block)
                return block
        return None

    def update(
        self,
        block_id: str,
        *,
        content: str,
        source: str = "interaction",
        tags: Optional[List[str]] = None,
        governance_status: Optional[str] = None,
        consistency_flags: Optional[List[Dict]] = None,
        embedding: Optional[List[float]] = None,
    ) -> Optional[MemoryBlock]:
        current = self._read_block(block_id)
        if not current or not current.active:
            return None

        snapshot_path = self._version_path(block_id, current.version)
        with open(snapshot_path, "w", encoding="utf-8") as fh:
            json.dump(current.model_dump_for_storage(), fh, ensure_ascii=False, indent=2)

        current.content = content[: current.limit]
        current.version += 1
        current.updated_at = datetime.now()
        current.source = source
        if tags is not None:
            current.tags = tags
        if governance_status is not None:
            current.governance_status = governance_status
        if consistency_flags is not None:
            current.consistency_flags = consistency_flags
        if embedding is not None:
            current.embedding = embedding

        self._write_block(current)
        self._register(current)
        self._append_provenance({
            "event": "update",
            "block_id": block_id,
            "label": current.label,
            "version": current.version,
            "source": source,
        })
        return current

    def delete(self, block_id: str) -> bool:
        current = self._read_block(block_id)
        if not current:
            return False

        current.active = False
        current.updated_at = datetime.now()
        self._untrack_aux_indexes(current)
        self._write_block(current)
        self._register(current)
        self._append_provenance({
            "event": "delete",
            "block_id": block_id,
            "label": current.label,
            "version": current.version,
        })
        return True

    def list_blocks(
        self,
        *,
        label: Optional[str] = None,
        category: Optional[str] = None,
        active_only: bool = True,
        sort_by_priority: bool = False,
    ) -> List[MemoryBlock]:
        results: List[MemoryBlock] = []
        for entry in self._index.values():
            if active_only and not entry.get("active", True):
                continue
            if label and entry.get("label") != label:
                continue
            if category and entry.get("category") != category:
                continue
            block = self._read_block(entry["block_id"])
            if block:
                results.append(block)
        if sort_by_priority:
            results.sort(
                key=lambda b: (b.priority, -b.last_access.timestamp()),
            )
        else:
            results.sort(key=lambda b: b.updated_at, reverse=True)
        return results

    def get_version_history(self, block_id: str) -> List[MemoryBlock]:
        history: List[MemoryBlock] = []
        version_dir = self.versions_dir / block_id
        if version_dir.exists():
            for path in sorted(version_dir.glob("v*.json")):
                with open(path, encoding="utf-8") as fh:
                    history.append(MemoryBlock.from_storage(json.load(fh)))
        current = self._read_block(block_id)
        if current:
            history.append(current)
        return history

    # ── Label-based convenience API (Letta-style) ──────────────────────

    def create_block(
        self,
        label: str,
        initial_content: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> MemoryBlock:
        existing = self.get_active_by_label(label)
        if existing and label in SINGLETON_LABELS:
            raise ValueError(f"Block '{label}' already exists. Use update_block() instead.")
        block = create_block_from_spec(label, initial_content, **kwargs)
        return self.create(block)

    def get_block(self, label: str, *, touch: bool = True) -> Optional[MemoryBlock]:
        return self.get_active_by_label(label, touch=touch)

    def update_block(
        self,
        label: str,
        new_content: Union[str, Dict[str, Any]],
        reason: str = "store_update",
    ) -> MemoryBlock:
        block = self.get_active_by_label(label)
        content = _content_to_str(new_content)
        if block is None:
            created = create_block_from_spec(label, new_content)
            return self.create(created)
        block.update_content(content, reason=reason)
        return self.save(block)

    def delete_block(self, label: str) -> bool:
        block = self.get_active_by_label(label)
        if not block:
            return False
        return self.delete(block.block_id)

    # ── Recall (HierarchicalRecallEngine L1 layer) ─────────────────────

    def recall_by_priority(
        self,
        top_k: int = 5,
        include_episodic: bool = True,
    ) -> List[MemoryBlock]:
        blocks = self.list_blocks(active_only=True, sort_by_priority=True)
        if not include_episodic:
            blocks = [b for b in blocks if not isinstance(b, EpisodicMemoryBlock)]
        return blocks[:top_k]

    def recall_episodic(
        self,
        episodic_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[EpisodicMemoryBlock]:
        results: List[EpisodicMemoryBlock] = []
        if episodic_type:
            for block_id in self._episodic_index.get(episodic_type, []):
                block = self._read_block(block_id)
                if (
                    block
                    and block.active
                    and isinstance(block, EpisodicMemoryBlock)
                    and block.episodic_type == episodic_type
                ):
                    results.append(block)
        else:
            for block in self.list_episodic_blocks():
                if isinstance(block, EpisodicMemoryBlock):
                    results.append(block)
        results.sort(key=lambda b: b.timestamp, reverse=True)
        return results[:limit]

    # ── Attention hybrid ─────────────────────────────────────────────

    def get_attention_snapshot(self) -> Optional[AttentionStateBlock]:
        if self._attention_snapshot and self._attention_snapshot.active:
            return self._attention_snapshot
        block = self.get_active_by_label("attention_state", touch=False)
        if isinstance(block, AttentionStateBlock):
            self._attention_snapshot = block
            return block
        return None

    def sync_attention_from_dynamic(
        self,
        focus_scores: Dict[str, float],
        top_focus: List[str],
        turn: int,
    ) -> AttentionStateBlock:
        snapshot = self.get_attention_snapshot()
        if snapshot is None:
            created = create_block_from_spec("attention_state")
            if not isinstance(created, AttentionStateBlock):
                created = AttentionStateBlock.from_label("attention_state", "{}")
            snapshot = self.create(created)  # type: ignore[assignment]
        snapshot.sync_from_dynamic(focus_scores, top_focus, turn)
        saved = self.save(snapshot)
        self._attention_snapshot = saved  # type: ignore[assignment]
        return saved  # type: ignore[return-value]

    # ── Lifecycle & governance helpers ─────────────────────────────────

    def apply_decay_all(self, hours_since_last: float) -> None:
        for block in self.list_blocks(active_only=True):
            decayed = block.decay(hours_since_last)
            if decayed < 0.3 and block.priority > 5:
                block.metadata["decay_warning"] = True
                self.save(block)

    def get_blocks_for_governance_check(self) -> List[MemoryBlock]:
        return [
            block
            for block in self.list_blocks(active_only=True)
            if block.priority <= 4 or "value" in block.label.lower()
        ]

    # ── Category listing ───────────────────────────────────────────────

    def list_core_blocks(self) -> List[MemoryBlock]:
        return self.list_blocks(category=BlockCategory.CORE.value)

    def list_archival_blocks(self) -> List[MemoryBlock]:
        return self.list_blocks(category=BlockCategory.ARCHIVAL.value)

    def list_episodic_blocks(self) -> List[MemoryBlock]:
        return self.list_blocks(category=BlockCategory.EPISODIC.value)

    @staticmethod
    def known_labels() -> List[str]:
        return list(BLOCK_SPECS.keys())

    @staticmethod
    def is_core_label(label: str) -> bool:
        return label in CORE_LABELS

    @staticmethod
    def is_archival_label(label: str) -> bool:
        return label in ARCHIVAL_LABELS

    @staticmethod
    def is_profile_label(label: str) -> bool:
        return label in PROFILE_LABELS

    @staticmethod
    def is_episodic_label(label: str) -> bool:
        return label in EPISODIC_LABELS

    # ── Stats & export ───────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        active = self.list_blocks(active_only=True)
        episodic_count = {key: len(ids) for key, ids in self._episodic_index.items()}
        last_updated = max((block.updated_at for block in active), default=None)
        return {
            "total_blocks": len(active),
            "by_priority": {block.label: block.priority for block in active},
            "episodic_counts": episodic_count,
            "has_attention_snapshot": self.get_attention_snapshot() is not None,
            "last_updated": last_updated.isoformat() if last_updated else None,
        }

    def to_json(self) -> str:
        active = self.list_blocks(active_only=True)
        return json.dumps(
            {
                "blocks": [block.to_dict() for block in active],
                "episodic_index": self._episodic_index,
                "stats": self.stats(),
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        )


if __name__ == "__main__":
    store = MemoryBlockStore("memory/demo_blocks")

    store.create_block(
        "persona",
        {"core_traits": ["curious", "empathetic"], "narrative": "CNexus persistent self"},
    )
    store.create_block("emotion", {"valence": 0.75, "mood": "focused_calm"})
    store.create_block("intent", {"active_goals": ["help user develop CNexus"]})

    event_blk = store.create_block("episodic_event")
    if isinstance(event_blk, EpisodicMemoryBlock):
        event_blk.add_structured_entry(
            {
                "action": "user chose Option 2 to fill episodic gap",
                "outcome": "success",
                "actors": ["user", "runtime"],
            }
        )
        store.save(event_blk)

    store.sync_attention_from_dynamic(
        focus_scores={"persona": 0.9, "working_memory": 0.7, "episodic_event": 0.4},
        top_focus=["persona", "working_memory"],
        turn=42,
    )

    print("=== CNexus MemoryBlockStore Demo (Option 2) ===")
    print("Stats:", store.stats())
    print("\nTop priority recall:")
    for block in store.recall_by_priority(5):
        print(f"  {block.label} (prio={block.priority}, version={block.version})")

    print("\nEpisodic events:")
    for entry in store.recall_episodic("event", 3):
        preview = entry.payload[:1] if entry.payload else "empty"
        print(f"  {entry.label} - {preview}")

    attn = store.get_attention_snapshot()
    if attn:
        snap = attn.read_snapshot()
        print(f"\nAttention snapshot last_sync_turn={snap.get('last_sync_turn')}")
