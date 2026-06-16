"""Persist synthesis snapshots for novelty / discovery diff."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from core.cse.types import CognitiveOutput

KindKey = Tuple[str, str]


class SynthesisSnapshotStore:
    """In-memory ring buffer — v1 sufficient for single-process Runtime."""

    def __init__(self, max_archive: int = 20) -> None:
        self._max_archive = max_archive
        self._archive: List[Dict[str, Any]] = []

    def fingerprint(self, output: CognitiveOutput) -> Set[KindKey]:
        keys: Set[KindKey] = set()
        for block in output.summary:
            keys.add(("summary", block.text[:80]))
        for block in output.patterns:
            keys.add(("pattern", block.text[:80]))
        for block in output.rules:
            keys.add(("rule", block.text[:80]))
        for ins in output.insights:
            keys.add(("insight", ins.title))
        for disc in output.discoveries:
            keys.add(("discovery", disc.title))
        return keys

    def last_fingerprint(self) -> Set[KindKey]:
        if not self._archive:
            return set()
        prev = self._archive[-1]
        return set(tuple(k) for k in prev.get("fingerprint", []))

    def commit(self, output: CognitiveOutput) -> None:
        fp = self.fingerprint(output)
        entry = {
            "generated_at": output.generated_at,
            "window_size": output.window_size,
            "fingerprint": [list(k) for k in fp],
            "narrative": output.narrative,
        }
        self._archive.append(entry)
        if len(self._archive) > self._max_archive:
            self._archive = self._archive[-self._max_archive :]

    def list_archive(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(reversed(self._archive[-limit:]))

    def previous_generated_at(self) -> Optional[str]:
        if len(self._archive) < 1:
            return None
        return str(self._archive[-1].get("generated_at") or "")


_global_store = SynthesisSnapshotStore()


def get_snapshot_store() -> SynthesisSnapshotStore:
    return _global_store
