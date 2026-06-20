"""L3-3 daily reflection scheduling — async L3 tick, never on chat fast lane."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_last_scheduled_day: Optional[str] = None


def _marker_path(runtime: Any) -> Optional[Path]:
    base = getattr(runtime, "base_dir", None)
    if not base:
        return None
    return Path(str(base)) / "observability" / ".last_daily_reflection"


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def already_consolidated_today(runtime: Any) -> bool:
    marker = _marker_path(runtime)
    if marker is None or not marker.is_file():
        return False
    try:
        return marker.read_text(encoding="utf-8").strip() == _today_utc()
    except OSError:
        return False


def mark_consolidated_today(runtime: Any) -> None:
    marker = _marker_path(runtime)
    if marker is None:
        return
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(_today_utc(), encoding="utf-8")
    except OSError as exc:
        logger.debug("reflection marker write failed: %s", exc)


def get_reflection_scheduler(runtime: Optional[Any], scheduler: Optional[Any] = None) -> Any:
    if scheduler is not None:
        return scheduler
    from core.runtime.attractor_background import get_attractor_scheduler

    return get_attractor_scheduler(runtime)


def enqueue_daily_reflection(
    runtime: Any,
    scheduler: Optional[Any] = None,
) -> bool:
    """Enqueue once-per-UTC-day consolidation onto L3 background queue."""
    global _last_scheduled_day
    today = _today_utc()
    if _last_scheduled_day == today or already_consolidated_today(runtime):
        return False

    from core.runtime.l3_scheduler import L3Task, L3TaskKind
    from core.personality.reflection.daily_consolidation import run_daily_consolidation
    from core.runtime.attractor_background import resolve_self_model_store

    sched = get_reflection_scheduler(runtime, scheduler)
    base_dir = str(getattr(runtime, "base_dir", "") or "")

    def _task() -> dict:
        store = resolve_self_model_store(runtime)
        result = run_daily_consolidation(store, base_dir=base_dir)
        if not result.get("skipped"):
            mark_consolidated_today(runtime)
        return result

    sched.enqueue(
        L3Task(
            kind=L3TaskKind.DAILY_REFLECTION,
            fn=_task,
            label="daily_reflection",
            estimated_cost_ms=80,
        )
    )
    _last_scheduled_day = today
    try:
        sched.run_tick()
    except Exception as exc:
        logger.debug("daily_reflection tick drain failed: %s", exc)
    return True


def run_daily_reflection_tick(runtime: Any, scheduler: Any) -> bool:
    """L3 tick hook — schedule daily consolidation when not yet run today."""
    try:
        return enqueue_daily_reflection(runtime, scheduler)
    except Exception as exc:
        logger.debug("daily_reflection tick failed: %s", exc)
        return False
