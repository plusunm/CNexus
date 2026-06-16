"""Prompt delta cache v2 — hash diff + zero-rebuild prompt cache."""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Callable, Dict, Optional

DeltaResult = Dict[str, Any]
CacheEntry = Dict[str, Any]

_global_delta_cache: Optional["PromptDeltaCacheV2"] = None
_global_prompt_cache: Optional["PromptCache"] = None
_cache_lock = threading.Lock()


def prompt_minimal_v2_enabled() -> bool:
    flag = os.environ.get("CNEXUS_PROMPT_MINIMAL_V2", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def stable_hash(obj: Any) -> int:
    try:
        payload = json.dumps(obj, sort_keys=True, default=str)
    except TypeError:
        payload = str(obj)
    return hash(payload)


class PromptDeltaCacheV2:
    """Semantic hash diff — reuse cached prompt/result when unchanged."""

    def __init__(self) -> None:
        self.last_hash: Optional[int] = None
        self.last_base: Optional[Dict[str, Any]] = None
        self.last_memory_hash: Optional[int] = None
        self.last_result: Optional[Any] = None

    def hash(self, obj: Any) -> int:
        return stable_hash(obj)

    def diff(self, new_base: Dict[str, Any]) -> DeltaResult:
        new_hash = self.hash(new_base)
        memory_hash = self.hash(new_base.get("memory_delta"))

        if self.last_hash == new_hash:
            return {"type": "reuse", "base_ref": "cached_prompt"}

        self.last_hash = new_hash
        self.last_base = dict(new_base)
        self.last_memory_hash = memory_hash
        return {"type": "delta", "base": new_base}

    def store_result(self, result: Any) -> None:
        self.last_result = result

    def reuse_result(self) -> Optional[Any]:
        return self.last_result


class PromptCache:
    """Zero-rebuild path — get_or_build keyed prompt cache."""

    def __init__(self) -> None:
        self.cache: Dict[str, Dict[str, Any]] = {}

    def get_or_build(self, key: str, builder: Callable[[], Dict[str, Any]]) -> CacheEntry:
        if key in self.cache:
            return {"type": "cached", "prompt": self.cache[key]}
        prompt = builder()
        self.cache[key] = prompt
        return {"type": "built", "prompt": prompt}

    def clear(self) -> None:
        self.cache.clear()


def get_runtime_delta_cache(runtime: Optional[Any] = None) -> PromptDeltaCacheV2:
    global _global_delta_cache
    if runtime is not None:
        existing = getattr(runtime, "_prompt_delta_cache_v2", None)
        if isinstance(existing, PromptDeltaCacheV2):
            return existing
        cache = PromptDeltaCacheV2()
        setattr(runtime, "_prompt_delta_cache_v2", cache)
        return cache
    with _cache_lock:
        if _global_delta_cache is None:
            _global_delta_cache = PromptDeltaCacheV2()
        return _global_delta_cache


def get_runtime_prompt_cache(runtime: Optional[Any] = None) -> PromptCache:
    global _global_prompt_cache
    if runtime is not None:
        existing = getattr(runtime, "_prompt_cache_v2", None)
        if isinstance(existing, PromptCache):
            return existing
        cache = PromptCache()
        setattr(runtime, "_prompt_cache_v2", cache)
        return cache
    with _cache_lock:
        if _global_prompt_cache is None:
            _global_prompt_cache = PromptCache()
        return _global_prompt_cache
