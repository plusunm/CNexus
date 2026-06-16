"""Execution graph v4 — intent routing without prompt compilation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.intent.llm_backend_v4 import LLMBackendV4, get_llm_backend_v4
from core.runtime.runtime_kernel import RuntimeKernel

logger = logging.getLogger(__name__)


class ExecutionGraphV4:
    """Direct intent → backend execution router."""

    def __init__(
        self,
        runtime: Optional[Any] = None,
        *,
        llm_backend: Optional[LLMBackendV4] = None,
    ) -> None:
        self.runtime = runtime
        self.llm_backend = llm_backend or get_llm_backend_v4(runtime)
        self._kernel = RuntimeKernel(runtime)

    async def execute(self, intent: str, payload: Dict[str, Any]) -> Any:
        key = str(intent)
        if key == "chat":
            return await self.llm_backend.generate(payload)

        if key == "status":
            return await self.system_probe(payload)

        if key == "memory_query":
            return await self.memory_query(payload)

        return {"status": "unknown_intent", "intent": key}

    async def system_probe(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        _ = payload
        return {
            "status": "ok",
            "l3": self._kernel.l3_queue_length(),
            "cluster": self._kernel.cluster_quick_probe(),
            "mode": "promptless_v4",
        }

    async def memory_query(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        runtime = self.runtime
        query = str(payload.get("query") or payload.get("input") or "")
        limit = int(payload.get("limit") or 5)
        if runtime is None:
            return {"items": [], "status": "ok"}

        storage = getattr(runtime, "storage", None)
        if storage is not None:
            recall = getattr(storage, "recall", None)
            if callable(recall):
                try:
                    raw = recall(query, limit=limit)
                except TypeError:
                    try:
                        raw = recall(query)
                    except Exception as exc:
                        logger.debug("memory_query recall failed: %s", exc)
                        raw = []
                except Exception as exc:
                    logger.debug("memory_query recall failed: %s", exc)
                    raw = []
                if isinstance(raw, list):
                    return {"items": raw[:limit], "status": "ok"}
                if isinstance(raw, str):
                    return {"items": [{"text": raw}], "status": "ok"}

        memory = getattr(runtime, "memory", None)
        query_fn = getattr(memory, "query", None) if memory is not None else None
        if callable(query_fn):
            try:
                items = await query_fn(payload) if _is_coroutine(query_fn) else query_fn(payload)
                return {"items": list(items or []), "status": "ok"}
            except Exception as exc:
                logger.debug("memory_query failed: %s", exc)

        return {"items": [], "status": "ok"}


def _is_coroutine(fn: Any) -> bool:
    import asyncio

    return asyncio.iscoroutinefunction(fn)


def get_execution_graph_v4(
    runtime: Optional[Any] = None,
    *,
    llm_backend: Optional[LLMBackendV4] = None,
) -> ExecutionGraphV4:
    if runtime is not None:
        existing = getattr(runtime, "_execution_graph_v4", None)
        if isinstance(existing, ExecutionGraphV4):
            return existing
        graph = ExecutionGraphV4(runtime, llm_backend=llm_backend)
        setattr(runtime, "_execution_graph_v4", graph)
        return graph
    return ExecutionGraphV4(None, llm_backend=llm_backend)
