"""Unified fast-lane prompt resolution — v3 compile > v2 delta > v1 minimal > raw."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Union

from core.prompt.context_enhancer_v1 import schedule_enrichment
from core.prompt.context_enhancer_v2 import schedule_delta_enrichment
from core.prompt.delta_cache_v2 import (
    get_runtime_delta_cache,
    get_runtime_prompt_cache,
    prompt_minimal_v2_enabled,
)
from core.prompt.execution_graph_v3 import get_graph_runner, tokens_to_llm_text
from core.prompt.minimal_builder_v1 import (
    extract_user_text,
    get_minimal_builder,
    prompt_minimal_v1_enabled,
)
from core.prompt.semantic_compiler_v3 import (
    get_semantic_compiler,
    get_token_cache,
    prompt_minimal_v3_enabled,
    stable_compile_hash,
)
from core.prompt.semantic_delta_v2 import get_semantic_delta_builder

PromptPayload = Union[str, Dict[str, Any]]
PrepareResult = Tuple[PromptPayload, str, bool]


def resolve_prompt_mode(
    *,
    compiler: Optional[Any] = None,
    delta_builder: Optional[Any] = None,
    builder: Optional[Any] = None,
) -> str:
    if compiler is not None:
        return "prompt_minimal_v3"
    if delta_builder is not None:
        return "prompt_minimal_v2"
    if builder is not None:
        return "prompt_minimal_v1"
    return "fast_lane_v1"


def init_prompt_builders(runtime: Optional[Any] = None) -> Dict[str, Any]:
    """Initialize v3/v2/v1 pipeline with precedence."""
    compiler = None
    runner = None
    token_cache = None
    delta_builder = None
    delta_cache = None
    prompt_cache = None
    builder = None

    if prompt_minimal_v3_enabled():
        compiler = get_semantic_compiler(runtime)
        runner = get_graph_runner(runtime)
        token_cache = get_token_cache(runtime)
        delta_builder = get_semantic_delta_builder(runtime)
    elif prompt_minimal_v2_enabled():
        delta_builder = get_semantic_delta_builder(runtime)
        delta_cache = get_runtime_delta_cache(runtime)
        prompt_cache = get_runtime_prompt_cache(runtime)
    elif prompt_minimal_v1_enabled():
        builder = get_minimal_builder(runtime)

    return {
        "compiler": compiler,
        "runner": runner,
        "token_cache": token_cache,
        "delta_builder": delta_builder,
        "delta_cache": delta_cache,
        "prompt_cache": prompt_cache,
        "builder": builder,
    }


def prepare_fast_lane_prompt(
    runtime: Optional[Any],
    user_input: str,
    *,
    intent: str = "chat",
    context_delta: Optional[Dict[str, Any]] = None,
    compiler: Optional[Any] = None,
    runner: Optional[Any] = None,
    token_cache: Optional[Any] = None,
    delta_builder: Optional[Any] = None,
    delta_cache: Optional[Any] = None,
    prompt_cache: Optional[Any] = None,
    builder: Optional[Any] = None,
) -> PrepareResult:
    """
    Returns (payload, mode, cache_hit).
    cache_hit=True means token/graph cache hit (v2: LLM result reuse).
    """
    if compiler is not None and runner is not None and token_cache is not None:
        return _prepare_compiled(
            runtime,
            user_input,
            intent=intent,
            context_delta=context_delta,
            compiler=compiler,
            runner=runner,
            token_cache=token_cache,
            delta_builder=delta_builder,
        )

    if delta_builder is not None and delta_cache is not None and prompt_cache is not None:
        return _prepare_delta(runtime, user_input, delta_builder, delta_cache, prompt_cache)

    if builder is not None:
        base = builder.build(user_input)
        schedule_enrichment(runtime, base)
        return base, "prompt_minimal_v1", False

    return user_input, "fast_lane_v1", False


def _prepare_compiled(
    runtime: Optional[Any],
    user_input: str,
    *,
    intent: str,
    context_delta: Optional[Dict[str, Any]],
    compiler: Any,
    runner: Any,
    token_cache: Any,
    delta_builder: Optional[Any],
) -> PrepareResult:
    delta = context_delta
    if delta is None and delta_builder is not None:
        built = delta_builder.build(user_input)
        delta = {
            "state_delta": built.get("state_delta"),
            "memory_delta": built.get("memory_delta"),
            "trace_id": built.get("trace_id"),
        }

    compiled = compiler.compile(intent, delta or {})
    token_key = stable_compile_hash(intent, user_input)
    cached_tokens = token_cache.get(token_key)
    if cached_tokens is not None:
        return (
            {
                "tokens": cached_tokens,
                "text": tokens_to_llm_text(cached_tokens),
                "mode": "minimal_v3",
                "execution": "cached_graph",
                "intent": intent,
                "token_cache_hit": True,
            },
            "prompt_minimal_v3",
            True,
        )

    result = runner.run(compiled["graph"], runtime, user_input, delta)
    token_cache.set(token_key, list(result.get("tokens") or []))
    if delta_builder is not None:
        schedule_delta_enrichment(runtime, {"input": user_input, **(delta or {}), "mode": "minimal_v3"})
    return result, "prompt_minimal_v3", False


def _prepare_delta(
    runtime: Optional[Any],
    user_input: str,
    delta_builder: Any,
    delta_cache: Any,
    prompt_cache: Any,
) -> PrepareResult:
    def _build() -> Dict[str, Any]:
        return delta_builder.build(user_input)

    entry = prompt_cache.get_or_build(user_input, _build)
    prompt = entry["prompt"]
    diff = delta_cache.diff(prompt)

    if diff["type"] == "reuse":
        return (
            {"cache_hit": True, "input": user_input, "mode": "minimal_v2"},
            "prompt_minimal_v2",
            True,
        )

    schedule_delta_enrichment(runtime, prompt)
    return prompt, "prompt_minimal_v2", False


def resolve_user_text(payload: PromptPayload) -> str:
    if isinstance(payload, dict):
        if payload.get("text"):
            return str(payload["text"])
        if payload.get("tokens"):
            return tokens_to_llm_text(list(payload["tokens"]))
    return extract_user_text(payload)
