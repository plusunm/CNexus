"""Streaming controller — attach progressive ready stream to runtime / frontend."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, Optional

from core.runtime.predictive_hydrate import schedule_predictive_hydration
from core.runtime.streaming_ready import StreamingReady, streaming_ready_ack

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task[Any]] = set()


def _track_task(task: asyncio.Task[Any]) -> None:
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def create_background_task(coro) -> asyncio.Task[Any]:
    """Schedule coroutine on the running loop (Fast-Path v2 helper)."""
    task = asyncio.create_task(coro)
    _track_task(task)
    return task


async def _dispatch_callback(callback: Callable[[Dict[str, Any]], Any], event: Dict[str, Any]) -> None:
    result = callback(event)
    if asyncio.iscoroutine(result):
        await result


async def system_ready_stream(
    runtime: Optional[Any],
    callback: Callable[[Dict[str, Any]], Any],
) -> Dict[str, Any]:
    """Start streaming ready phases without blocking the caller."""

    async def _runner() -> None:
        streamer = StreamingReady(runtime)

        async def _cb(event: Dict[str, Any]) -> None:
            await _dispatch_callback(callback, event)

        try:
            await streamer.stream_ready(_cb)
        except Exception as exc:
            logger.warning("StreamingReady failed: %s", exc)

    schedule_predictive_hydration(runtime)
    create_background_task(_runner())
    return streaming_ready_ack()


async def attach_stream(
    runtime: Optional[Any],
    frontend: Any,
) -> Dict[str, Any]:
    """Wire runtime stream to a frontend `on_stream` handler."""

    async def handler(event: Dict[str, Any]) -> None:
        on_stream = getattr(frontend, "on_stream", None)
        if callable(on_stream):
            await _dispatch_callback(on_stream, event)

    return await system_ready_stream(runtime, handler)


async def iter_ready_sse(runtime: Optional[Any]) -> AsyncIterator[str]:
    """Server-Sent Events lines for GET /v1/system/ready/stream."""
    schedule_predictive_hydration(runtime)
    streamer = StreamingReady(runtime)
    async for event in streamer.iter_events():
        yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
