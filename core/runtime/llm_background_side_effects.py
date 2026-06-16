"""LLM fast lane background side effects — never block the main chat path."""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.runtime.llm_executor_pool import ExecutorPool

logger = logging.getLogger(__name__)


def schedule_background_side_effects(runtime: Optional[Any], prompt: str = "") -> None:
    ExecutorPool.background_executor().submit(_run_side_effects, runtime, prompt)


def _run_side_effects(runtime: Optional[Any], prompt: str) -> None:
    try:
        _memory_recall_async(runtime, prompt)
        _embedding_update_hot(runtime)
        _crdt_merge_lazy()
    except Exception as exc:
        logger.debug("background_side_effects failed: %s", exc)


def _memory_recall_async(runtime: Optional[Any], prompt: str) -> None:
    if runtime is None or not prompt:
        return
    storage = getattr(runtime, "storage", None)
    if storage is None:
        return
    recall = getattr(storage, "recall", None)
    if not callable(recall):
        return
    try:
        recall(prompt, limit=3)
    except TypeError:
        try:
            recall(prompt)
        except Exception:
            pass
    except Exception:
        pass


def _embedding_update_hot(runtime: Optional[Any]) -> None:
    if runtime is None:
        return
    mm = getattr(runtime, "memory_manager", None)
    if mm is not None and hasattr(mm, "block_stats"):
        try:
            mm.block_stats()
        except Exception:
            pass


def _crdt_merge_lazy() -> None:
    try:
        from core.runtime.system_guard import non_hang_v5_enabled

        if not non_hang_v5_enabled():
            return
        from core.kernel.v5.crdt_memory import get_crdt_memory

        get_crdt_memory().stats()
    except Exception:
        pass
