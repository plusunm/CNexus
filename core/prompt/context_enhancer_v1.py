"""Async prompt enrichment v1 — Layer-1 probes + Layer-2 background offload."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from core.prompt.minimal_builder_v1 import PromptDict
from core.runtime.async_bridge import run_coro_sync
from core.runtime.event_loop_offload import offload_sync
from core.runtime.runtime_kernel import RuntimeKernel

logger = logging.getLogger(__name__)

EnrichedPrompt = Dict[str, Any]


async def memory_probe(runtime: Optional[Any], *, limit: int = 5) -> Dict[str, Any]:
    """Non-blocking hot memory peek — never blocks request path."""

    def _peek() -> Dict[str, Any]:
        if runtime is None:
            return {"items": []}
        memory = getattr(runtime, "memory", None)
        if memory is not None:
            peek_hot = getattr(memory, "peek_hot", None)
            if callable(peek_hot):
                try:
                    items = peek_hot(limit=limit)
                    return {"items": list(items or [])[:limit]}
                except TypeError:
                    try:
                        items = peek_hot(limit)
                        return {"items": list(items or [])[:limit]}
                    except Exception:
                        pass
                except Exception:
                    pass
        storage = getattr(runtime, "storage", None)
        if storage is None:
            return {"items": []}
        recall = getattr(storage, "recall", None)
        if not callable(recall):
            return {"items": []}
        try:
            raw = recall("", limit=limit)
        except TypeError:
            try:
                raw = recall("")
            except Exception:
                return {"items": []}
        except Exception:
            return {"items": []}
        if isinstance(raw, list):
            return {"items": raw[:limit]}
        if isinstance(raw, str) and raw.strip():
            return {"items": [{"text": raw[:500]}]}
        return {"items": []}

    try:
        return await offload_sync(_peek, timeout_s=2.0)
    except Exception as exc:
        logger.debug("memory_probe failed: %s", exc)
        return {"items": []}


async def governance_probe(runtime: Optional[Any]) -> Dict[str, Any]:
    """Light non-blocking governance peek."""

    def _peek() -> Dict[str, Any]:
        if runtime is None:
            return {"risk": "low", "mode": "non_blocking"}
        gov = getattr(runtime, "governance", None)
        peek = getattr(gov, "peek_non_blocking", None) if gov is not None else None
        if callable(peek):
            try:
                snapshot = peek()
                if isinstance(snapshot, dict):
                    snapshot.setdefault("mode", "non_blocking")
                    return snapshot
            except Exception:
                pass
        return {"risk": "low", "mode": "non_blocking"}

    try:
        return await offload_sync(_peek, timeout_s=1.0)
    except Exception:
        return {"risk": "low", "mode": "non_blocking"}


async def runtime_snapshot_light(runtime: Optional[Any]) -> Dict[str, Any]:
    """Minimal runtime state — L3 queue + cluster probe only."""

    def _snapshot() -> Dict[str, Any]:
        kernel = RuntimeKernel(runtime)
        return {
            "l3": kernel.l3_queue_length(),
            "cluster": kernel.cluster_quick_probe(),
            "mode": "light",
        }

    try:
        return await offload_sync(_snapshot, timeout_s=1.5)
    except Exception:
        return {"l3": 0, "cluster": "deferred", "mode": "light"}


async def async_offload(runtime: Optional[Any], task_name: str) -> Any:
    """Await named cognitive offload — maps spec task names to probes."""
    name = str(task_name)
    if name in ("memory.recall_hot_async", "memory.recall_async", "memory.peek_hot"):
        return await memory_probe(runtime)
    if name in ("runtime.snapshot_light", "runtime.snapshot"):
        return await runtime_snapshot_light(runtime)
    if name in ("governance.peek_non_blocking", "governance.peek"):
        return await governance_probe(runtime)
    logger.debug("async_offload unknown task: %s", name)
    return None


async def enrich_prompt_async(
    runtime: Optional[Any],
    base_prompt: PromptDict,
) -> EnrichedPrompt:
    """Layer-1 async enrichment — memory, state, policy."""
    memory = await async_offload(runtime, "memory.recall_hot_async")
    state = await async_offload(runtime, "runtime.snapshot_light")
    policy = await async_offload(runtime, "governance.peek_non_blocking")
    enriched: EnrichedPrompt = {
        **base_prompt,
        "memory": memory,
        "state": state,
        "policy": policy,
        "enriched": True,
    }
    if runtime is not None:
        setattr(runtime, "_last_enriched_prompt", enriched)
    schedule_layer2_background(runtime, base_prompt)
    return enriched


def schedule_layer2_background(runtime: Optional[Any], base_prompt: PromptDict) -> None:
    """Layer-2 — CDG / spine / debug linkage (never blocks chat path)."""
    kernel = RuntimeKernel(runtime)

    def _layer2() -> None:
        try:
            from core.runtime.linkage_debug import build_linkage_debug_payload

            build_linkage_debug_payload(app_started=True, peek_runtime=lambda: runtime)
        except Exception as exc:
            logger.debug("layer2 linkage_debug skipped: %s", exc)
        try:
            from core.runtime.introspection import build_runtime_introspection

            if runtime is not None and hasattr(runtime, "memory_manager"):
                build_runtime_introspection(runtime)
        except Exception as exc:
            logger.debug("layer2 introspection skipped: %s", exc)

    kernel.offload(_layer2)


def schedule_enrichment(runtime: Optional[Any], base_prompt: PromptDict) -> None:
    """Fire-and-forget Layer-1 enrichment — does not block LLM generate."""

    async def _run() -> None:
        try:
            await enrich_prompt_async(runtime, base_prompt)
        except Exception as exc:
            logger.debug("schedule_enrichment failed: %s", exc)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run())
    except RuntimeError:
        run_coro_sync(enrich_prompt_async(runtime, base_prompt))
