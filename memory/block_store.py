"""MemoryBlockStore — structured block CRUD with version control."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from memory.block import (
    ARCHIVAL_LABELS,
    BLOCK_SPECS,
    BlockCategory,
    CORE_LABELS,
    MemoryBlock,
    PROFILE_LABELS,
    SINGLETON_LABELS,
)


class MemoryBlockStore:
    """Manages structured Memory Blocks with CRUD + version history."""

    def __init__(self, blocks_dir: str | Path):
        self.blocks_dir = Path(blocks_dir)
        self.blocks_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir = self.blocks_dir / "versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.blocks_dir / "index.json"
        self.provenance_path = self.blocks_dir / "provenance.jsonl"
        self._index: Dict[str, dict] = self._load_index()

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

    # ── CRUD ───────────────────────────────────────────────────────────

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
        """Persist block state without creating a new version."""
        block.updated_at = datetime.now()
        self._write_block(block)
        self._register(block)
        return block

    def touch_access(self, block_id: str) -> Optional[MemoryBlock]:
        block = self._read_block(block_id)
        if not block or not block.active:
            return None
        block.last_accessed_at = datetime.now()
        return self.save(block)

    def get_all_blocks(self, *, active_only: bool = True) -> List[MemoryBlock]:
        return self.list_blocks(active_only=active_only)

    def get_active_by_label(self, label: str) -> Optional[MemoryBlock]:
        for entry in self._index.values():
            if entry.get("label") == label and entry.get("active", True):
                return self._read_block(entry["block_id"])
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

    def list_core_blocks(self) -> List[MemoryBlock]:
        return self.list_blocks(category=BlockCategory.CORE.value)

    def list_archival_blocks(self) -> List[MemoryBlock]:
        return self.list_blocks(category=BlockCategory.ARCHIVAL.value)

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
