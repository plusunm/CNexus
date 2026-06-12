"""Sleep-time Compute — offline archival compression and batch meta-reflection."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, Field

from core.governance.values_governance import VALUE_ALIGNMENT_LABEL
from core.personality.reflective.reflective_engine import REFLECTIVE_LABEL
from memory.manager import MemoryManager

if TYPE_CHECKING:
    from core.personality.reflective.reflective_engine import ReflectiveEngine


class ConsolidationReport(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    blocks_processed: int = 0
    reflective_compressed: int = 0
    value_alignment_compressed: int = 0
    archival_compressed: int = 0
    batch_reflections_generated: int = 0
    skipped: bool = False
    reason: Optional[str] = None
    errors: List[str] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


class SleepTimeCompute:
    """
    Letta-style sleep-time consolidation:
    compress archival traces, then optionally run batch meta-reflection.
    """

    def __init__(
        self,
        memory_manager: MemoryManager,
        reflective_engine: Optional["ReflectiveEngine"] = None,
        *,
        compression_threshold_days: int = 7,
        max_reflective_per_batch: int = 50,
        min_batch_reflections: int = 3,
    ):
        self.memory = memory_manager
        self.reflective = reflective_engine
        self.compression_threshold_days = compression_threshold_days
        self.max_reflective_per_batch = max_reflective_per_batch
        self.min_batch_reflections = min_batch_reflections

    async def run_sleep_cycle_async(self, *, force: bool = False) -> ConsolidationReport:
        """Async entry — suitable for FastAPI background tasks."""
        return await asyncio.to_thread(self.run_sleep_cycle, force=force)

    def run_sleep_cycle(self, *, force: bool = False) -> ConsolidationReport:
        """Synchronous sleep-time consolidation cycle."""
        report = ConsolidationReport()

        try:
            report.reflective_compressed = self._compress_reflective_trace(force=force)
            report.value_alignment_compressed = self._compress_value_alignment_history(
                force=force
            )
            report.archival_compressed = self._compress_archival_blocks()
            if self.reflective:
                report.batch_reflections_generated = self._batch_reflect_on_past()

            report.blocks_processed = (
                report.reflective_compressed
                + report.value_alignment_compressed
                + report.archival_compressed
            )
        except Exception as exc:
            report.errors.append(str(exc))

        return report

    def _cutoff(self, *, force: bool, multiplier: float = 1.0) -> datetime:
        if force:
            return datetime.now()
        days = max(1, int(self.compression_threshold_days * multiplier))
        return datetime.now() - timedelta(days=days)

    @staticmethod
    def _parse_json_content(content: str) -> Optional[Dict[str, Any]]:
        if not content or not str(content).strip().startswith("{"):
            return None
        try:
            data = json.loads(content)
            return data if isinstance(data, dict) else None
        except (json.JSONDecodeError, TypeError, ValueError):
            return None

    def _compress_reflective_trace(self, *, force: bool) -> int:
        blocks = self.memory.blocks.list_blocks(label=REFLECTIVE_LABEL, active_only=True)
        if not blocks:
            return 0

        cutoff = self._cutoff(force=force)
        compressed = 0

        for block in blocks:
            if block.protected:
                continue
            if not force and block.created_at >= cutoff:
                continue

            parsed = self._parse_json_content(block.content)
            if not parsed or parsed.get("compressed"):
                continue

            summary = self._summarize_reflection(parsed)
            parsed["compressed"] = True
            parsed["sleep_summary"] = summary
            reflection = str(parsed.get("reflection", ""))
            if len(reflection) > 200:
                parsed["reflection"] = summary

            payload = json.dumps(parsed, ensure_ascii=False)
            updated = self.memory.update_block(
                block.block_id,
                payload,
                source="sleep_time_compute",
            )
            if isinstance(updated, dict):
                continue

            stored = self.memory.get_block(block.block_id)
            if stored:
                stored.importance = min(stored.importance, 0.35)
                if "sleep_compressed" not in stored.tags:
                    stored.tags = list(stored.tags) + ["sleep_compressed"]
                self.memory.blocks.save(stored)
            compressed += 1

        return compressed

    def _compress_value_alignment_history(self, *, force: bool) -> int:
        blocks = self.memory.blocks.list_blocks(
            label=VALUE_ALIGNMENT_LABEL,
            active_only=True,
        )
        if not blocks:
            return 0

        cutoff = self._cutoff(force=force, multiplier=2.0)
        compressed = 0

        for block in blocks:
            if block.protected:
                continue
            if not force and block.created_at >= cutoff:
                continue

            parsed = self._parse_json_content(block.content)
            if not parsed or parsed.get("archived"):
                continue

            status = str(parsed.get("status", ""))
            score = float(parsed.get("alignment_score", 0.0) or 0.0)
            if status != "aligned" or score <= 0.8:
                continue

            parsed["archived"] = True
            parsed["sleep_archived_at"] = datetime.now().isoformat()
            payload = json.dumps(parsed, ensure_ascii=False)
            updated = self.memory.update_block(
                block.block_id,
                payload,
                source="sleep_time_compute",
            )
            if isinstance(updated, dict):
                continue

            stored = self.memory.get_block(block.block_id)
            if stored:
                stored.importance = min(stored.importance, 0.2)
                if "sleep_archived" not in stored.tags:
                    stored.tags = list(stored.tags) + ["sleep_archived"]
                self.memory.blocks.save(stored)
            compressed += 1

        return compressed

    def _compress_archival_blocks(self) -> int:
        result = self.memory.compress_archival_blocks()
        return int(result.get("compressed", 0) or 0)

    def _batch_reflect_on_past(self) -> int:
        if not self.reflective:
            return 0

        blocks = self.memory.blocks.list_blocks(label=REFLECTIVE_LABEL, active_only=True)
        if len(blocks) < self.min_batch_reflections:
            return 0

        generated = 0
        for block in blocks[: self.max_reflective_per_batch]:
            parsed = self._parse_json_content(block.content)
            if not parsed:
                continue
            actor_output = str(parsed.get("actor_output", ""))
            if not actor_output:
                continue
            try:
                self.reflective.reflect_on_interaction(
                    actor_output,
                    {
                        "source": "sleep_time_batch",
                        "reflection_id": parsed.get("reflection_id"),
                        "batch": True,
                    },
                    feedback="离线批量反思（sleep-time）",
                    importance=0.68,
                )
                generated += 1
            except Exception:
                continue

        return generated

    @staticmethod
    def _summarize_reflection(content: Dict[str, Any]) -> str:
        reflection = str(content.get("reflection", ""))
        if len(reflection) <= 200:
            return reflection
        return reflection[:200] + "..."
