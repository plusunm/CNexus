"""Semantic prompt compiler v3 — intent → compiled execution graph."""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, Optional

CompiledResult = Dict[str, Any]

_global_compiler: Optional["SemanticPromptCompilerV3"] = None
_compiler_lock = threading.Lock()

DEFAULT_GRAPH_NODES = [
    {"op": "inject_user_input"},
    {"op": "apply_context_delta"},
    {"op": "apply_memory_diff"},
    {"op": "apply_policy_light"},
    {"op": "emit_prompt_tokens"},
]


def prompt_minimal_v3_enabled() -> bool:
    flag = os.environ.get("CNEXUS_PROMPT_MINIMAL_V3", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def stable_compile_hash(intent: str, context_delta: Any) -> int:
    try:
        payload = json.dumps(
            {"intent": intent, "delta": context_delta},
            sort_keys=True,
            default=str,
        )
    except TypeError:
        payload = f"{intent}:{context_delta}"
    return hash(payload)


class SemanticPromptCompilerV3:
    """Compile intent + context delta into reusable token instruction graph."""

    def __init__(self) -> None:
        self.compiled_cache: Dict[int, Dict[str, Any]] = {}

    def compile(self, intent: str, context_delta: Optional[Dict[str, Any]] = None) -> CompiledResult:
        delta = context_delta or {}
        key = self._hash(intent, delta)
        if key in self.compiled_cache:
            return {
                "type": "cached_graph",
                "graph": self.compiled_cache[key],
                "compile_key": key,
            }

        graph = {
            "intent": str(intent),
            "context_delta": delta,
            "nodes": list(DEFAULT_GRAPH_NODES),
        }
        self.compiled_cache[key] = graph
        return {
            "type": "compiled_graph",
            "graph": graph,
            "compile_key": key,
        }

    def _hash(self, intent: str, context_delta: Dict[str, Any]) -> int:
        return stable_compile_hash(intent, context_delta)


class TokenCacheV3:
    """Token-level execution cache — graph output reuse."""

    def __init__(self) -> None:
        self.cache: Dict[int, list[Any]] = {}

    def get(self, key: int) -> Optional[list[Any]]:
        return self.cache.get(key)

    def set(self, key: int, tokens: list[Any]) -> None:
        self.cache[key] = list(tokens)

    def clear(self) -> None:
        self.cache.clear()


def get_semantic_compiler(runtime: Optional[Any] = None) -> SemanticPromptCompilerV3:
    if runtime is not None:
        existing = getattr(runtime, "_semantic_compiler_v3", None)
        if isinstance(existing, SemanticPromptCompilerV3):
            return existing
        compiler = SemanticPromptCompilerV3()
        setattr(runtime, "_semantic_compiler_v3", compiler)
        return compiler
    global _global_compiler
    with _compiler_lock:
        if _global_compiler is None:
            _global_compiler = SemanticPromptCompilerV3()
        return _global_compiler


def get_token_cache(runtime: Optional[Any] = None) -> TokenCacheV3:
    if runtime is not None:
        existing = getattr(runtime, "_token_cache_v3", None)
        if isinstance(existing, TokenCacheV3):
            return existing
        cache = TokenCacheV3()
        setattr(runtime, "_token_cache_v3", cache)
        return cache
    return TokenCacheV3()
