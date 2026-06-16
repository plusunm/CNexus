"""Predictive hydration — preload hot paths while UI streams ready phases."""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

_predictive_lock = threading.Lock()
_predictive_started = False


def schedule_predictive_hydration(runtime: Optional[Any] = None) -> bool:
    with _predictive_lock:
        global _predictive_started
        if _predictive_started:
            return False
        _predictive_started = True

    threading.Thread(
        target=_run_predictive,
        args=(runtime,),
        name="cnexus-predictive-hydrate-v2",
        daemon=True,
    ).start()
    return True


def _run_predictive(runtime: Optional[Any]) -> None:
    try:
        _preload_embedding(runtime)
        _prefetch_replay_hot_path()
        _lazily_merge_crdt()
        logger.info("Predictive hydration v2 complete")
    except Exception as exc:
        logger.warning("Predictive hydration v2 failed: %s", exc)


def _preload_embedding(runtime: Optional[Any]) -> None:
    if runtime is None:
        return
    mm = getattr(runtime, "memory_manager", None)
    if mm is not None and hasattr(mm, "block_stats"):
        try:
            mm.block_stats()
        except Exception:
            pass
    storage = getattr(runtime, "storage", None)
    vector = getattr(storage, "vector", None) if storage is not None else None
    if vector is not None and hasattr(vector, "table"):
        try:
            table = vector.table
            if hasattr(table, "count_rows"):
                table.count_rows()
        except Exception:
            pass


def _prefetch_replay_hot_path() -> None:
    try:
        from core.runtime.system_guard import non_hang_v4_enabled, non_hang_v5_enabled

        if not (non_hang_v4_enabled() or non_hang_v5_enabled()):
            return
        from core.kernel.v4.replay_engine import get_replay_engine

        engine = get_replay_engine()
        engine.verify_consistent(
            {
                "l3.task": lambda e: {
                    "type": "l3.task",
                    "id": e.get("id"),
                    "status": "predictive_prefetch",
                }
            }
        )
    except Exception:
        pass


def _lazily_merge_crdt() -> None:
    try:
        from core.runtime.system_guard import non_hang_v5_enabled

        if not non_hang_v5_enabled():
            return
        from core.kernel.v5.crdt_memory import get_crdt_memory

        crdt = get_crdt_memory()
        crdt.stats()
    except Exception:
        pass
