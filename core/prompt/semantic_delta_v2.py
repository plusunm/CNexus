"""Semantic delta builder v2 — state/memory diff-only prompt construction."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.prompt.minimal_builder_v1 import resolve_trace_id
from core.runtime.runtime_kernel import RuntimeKernel

DeltaPrompt = Dict[str, Any]


class RuntimeState:
    """Diffable light runtime state snapshot."""

    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime
        self._state: Dict[str, Any] = {}

    def snapshot_light(self) -> Dict[str, Any]:
        kernel = RuntimeKernel(self.runtime)
        return {
            "l3": kernel.l3_queue_length(),
            "cluster": kernel.cluster_quick_probe(),
            "mode": "light",
        }

    def diff(self, new_state: Dict[str, Any]) -> Dict[str, Any]:
        changed_keys = [k for k in new_state if self._state.get(k) != new_state[k]]
        values = {k: new_state[k] for k in changed_keys}
        self._state = dict(new_state)
        return {
            "changed_keys": changed_keys,
            "values": values,
            "has_changes": bool(changed_keys),
        }


class MemoryDeltaAdapter:
    """Diffable memory fingerprint — hot-key delta only."""

    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime
        self.last_fingerprint: Optional[int] = None
        self._last_hot_keys: List[str] = []

    def fingerprint(self) -> int:
        runtime = self.runtime
        if runtime is None:
            return 0
        memory = getattr(runtime, "memory", None)
        if memory is not None:
            fp_fn = getattr(memory, "fingerprint", None)
            if callable(fp_fn):
                try:
                    return int(fp_fn())
                except Exception:
                    pass
            peek_hot = getattr(memory, "peek_hot", None)
            if callable(peek_hot):
                try:
                    items = peek_hot(limit=5)
                    return stable_fingerprint(items)
                except Exception:
                    pass
        storage = getattr(runtime, "storage", None)
        if storage is not None:
            recall = getattr(storage, "recall", None)
            if callable(recall):
                try:
                    raw = recall("", limit=3)
                    return stable_fingerprint(raw)
                except Exception:
                    pass
        return 0

    def get_hot_delta(self) -> List[str]:
        runtime = self.runtime
        keys: List[str] = []
        if runtime is None:
            return keys
        memory = getattr(runtime, "memory", None)
        if memory is not None:
            hot_fn = getattr(memory, "get_hot_delta", None)
            if callable(hot_fn):
                try:
                    keys = list(hot_fn() or [])
                    return [str(k) for k in keys]
                except Exception:
                    pass
            peek_hot = getattr(memory, "peek_hot", None)
            if callable(peek_hot):
                try:
                    items = peek_hot(limit=5)
                    keys = [_hot_key(item) for item in (items or [])]
                except Exception:
                    pass
        current = [k for k in keys if k not in self._last_hot_keys]
        self._last_hot_keys = list(keys)
        return current

    def diff(self, fingerprint: int) -> Dict[str, Any]:
        changed = fingerprint != self.last_fingerprint
        hot_keys = self.get_hot_delta() if changed else []
        self.last_fingerprint = fingerprint
        return {
            "changed": changed,
            "hot_keys": hot_keys,
            "fingerprint": fingerprint,
        }


def stable_fingerprint(obj: Any) -> int:
    try:
        return hash(str(obj))
    except Exception:
        return 0


def _hot_key(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("id") or item.get("key") or item.get("text") or item)[:64]
    return str(item)[:64]


class SemanticDeltaBuilder:
    """Build delta-only prompt — never full state/memory rebuild."""

    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime
        self.state = RuntimeState(runtime)
        self.memory = MemoryDeltaAdapter(runtime)

    def build(self, user_input: str) -> DeltaPrompt:
        current_state = self.state.snapshot_light()
        memory_fingerprint = self.memory.fingerprint()
        return {
            "input": str(user_input),
            "trace_id": resolve_trace_id(self.runtime),
            "state_delta": self.state.diff(current_state),
            "memory_delta": self.memory.diff(memory_fingerprint),
            "mode": "minimal_v2",
        }


def get_semantic_delta_builder(runtime: Optional[Any] = None) -> SemanticDeltaBuilder:
    if runtime is not None:
        existing = getattr(runtime, "_semantic_delta_builder_v2", None)
        if isinstance(existing, SemanticDeltaBuilder):
            return existing
        builder = SemanticDeltaBuilder(runtime)
        setattr(runtime, "_semantic_delta_builder_v2", builder)
        return builder
    return SemanticDeltaBuilder(None)
