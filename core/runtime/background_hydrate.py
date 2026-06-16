"""Background hydration — replay / CRDT / embedding off the first-paint path."""

from __future__ import annotations

import logging
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

_hydrate_lock = threading.Lock()
_hydrate_started = False


def schedule_background_hydrate(runtime: Optional[Any] = None) -> bool:
    """Fire-and-forget heavy hydrate; safe to call from fast-path bootstrap."""
    global _hydrate_started
    with _hydrate_lock:
        if _hydrate_started:
            return False
        _hydrate_started = True

    threading.Thread(
        target=_run_hydrate,
        args=(runtime,),
        name="cnexus-bg-hydrate-v1",
        daemon=True,
    ).start()
    return True


def _run_hydrate(runtime: Optional[Any]) -> None:
    try:
        _hydrate_replay()
        _hydrate_crdt()
        _hydrate_embedding(runtime)
        logger.info("Background hydrate v1 complete")
    except Exception as exc:
        logger.warning("Background hydrate v1 failed: %s", exc)


def _hydrate_replay() -> None:
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
                    "status": "bg_hydrate",
                }
            }
        )
    except Exception:
        pass


def _hydrate_crdt() -> None:
    try:
        from core.runtime.system_guard import non_hang_v5_enabled

        if not non_hang_v5_enabled():
            return
        from core.kernel.v5.crdt_memory import get_crdt_memory

        get_crdt_memory().stats()
    except Exception:
        pass


def _hydrate_embedding(runtime: Optional[Any]) -> None:
    if runtime is None:
        return
    storage = getattr(runtime, "storage", None)
    vector = getattr(storage, "vector", None) if storage is not None else None
    table = getattr(vector, "table", None) if vector is not None else None
    if table is None:
        return
    try:
        if hasattr(table, "count_rows"):
            table.count_rows()
    except Exception:
        pass
