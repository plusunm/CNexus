"""CP-2 — execute write intents with Tier-A rollback on failure."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING, TypeVar

from core.governance.gtbs.state_snapshot import restore_tier_a, snapshot_for_intent, snapshot_tier_a
from core.governance.gtbs.write_intent import WriteIntent
from core.governance.gtbs.write_intent_bus import shadow_emit_enabled, soft_commit_enabled

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime

T = TypeVar("T")


def _last_spine_event_id() -> Optional[str]:
    from core.runtime.trace_context import get_trace_id
    from core.spine.integration import get_spine_writer

    writer = get_spine_writer()
    trace_id = get_trace_id()
    if writer is None or not trace_id:
        return None
    return writer.last_event_id(trace_id)


def _record_tier_a_diff(
    before,
    after,
    *,
    intent_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
) -> None:
    from core.spine.state.emit import maybe_record_tier_a_diff

    maybe_record_tier_a_diff(before, after, intent_id=intent_id, triggered_by=triggered_by)


def tx_rollback_enabled(*, config: Optional[Dict[str, Any]] = None) -> bool:
    gtbs = (config or {}).get("gtbs") or {}
    if "enable_write_intent_tx_rollback" in gtbs:
        return bool(gtbs["enable_write_intent_tx_rollback"])
    env = os.environ.get("GTBS_WRITE_INTENT_TX_ROLLBACK", "").strip().lower()
    return env in ("1", "true", "yes")


def funnel_active(*, config: Optional[Dict[str, Any]] = None) -> bool:
    return (
        shadow_emit_enabled(config=config)
        or soft_commit_enabled(config=config)
        or tx_rollback_enabled(config=config)
    )


def execute_with_tier_a_rollback(
    runtime: "BrainMemoryRuntime",
    execute: Callable[[], T],
    *,
    intent_id: Optional[str] = None,
    tier_b_meta: Optional[Dict[str, Any]] = None,
    record_commit: bool = True,
) -> T:
    """Snapshot Tier-A, execute, optional commit receipt or rollback — no intent re-emit."""
    config = getattr(runtime, "config", None)
    bus = runtime._get_write_intent_bus()
    snap = None
    before = snapshot_tier_a(runtime)
    if tx_rollback_enabled(config=config):
        snap = snapshot_for_intent(runtime, tier_b_meta=tier_b_meta)
    try:
        result = execute()
        after = snapshot_tier_a(runtime)
        _record_tier_a_diff(
            before,
            after,
            intent_id=intent_id,
            triggered_by=_last_spine_event_id(),
        )
        if intent_id and record_commit:
            bus.record_shadow_commit(
                intent_id,
                receipt={
                    "ok": True,
                    "tier_a_snapshot": snap is not None,
                    "tier_b_meta": tier_b_meta or {},
                },
            )
        return result
    except Exception as exc:
        if snap is not None:
            restore_tier_a(runtime, snap.tier_a)
            if intent_id:
                bus.record_rollback(intent_id, reason=str(exc), tier="A")
        raise


def execute_write_intent(
    runtime: "BrainMemoryRuntime",
    intent: WriteIntent,
    execute: Callable[[], T],
    *,
    tier_b_meta: Optional[Dict[str, Any]] = None,
) -> T:
    """Emit intent, optionally snapshot Tier-A, execute, commit or rollback."""
    config = getattr(runtime, "config", None)
    bus = runtime._get_write_intent_bus()
    intent_id = bus.emit(intent, config=config)
    intent_event_id = _last_spine_event_id()
    snap = None
    before = snapshot_tier_a(runtime)
    if tx_rollback_enabled(config=config):
        snap = snapshot_for_intent(runtime, tier_b_meta=tier_b_meta)
    try:
        result = execute()
        after = snapshot_tier_a(runtime)
        _record_tier_a_diff(
            before,
            after,
            intent_id=intent_id,
            triggered_by=intent_event_id,
        )
        bus.record_shadow_commit(
            intent_id,
            receipt={
                "ok": True,
                "tier_a_snapshot": snap is not None,
                "tier_b_meta": tier_b_meta or {},
            },
        )
        return result
    except Exception as exc:
        if snap is not None:
            restore_tier_a(runtime, snap.tier_a)
            bus.record_rollback(intent_id, reason=str(exc), tier="A")
        raise


def maybe_execute_write_intent(
    runtime: "BrainMemoryRuntime",
    build_intent: Callable[[], WriteIntent],
    execute: Callable[[], T],
    *,
    tier_b_meta: Optional[Dict[str, Any]] = None,
) -> T:
    if not funnel_active(config=getattr(runtime, "config", None)):
        return execute()
    return execute_write_intent(
        runtime,
        build_intent(),
        execute,
        tier_b_meta=tier_b_meta,
    )
