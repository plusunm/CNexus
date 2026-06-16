"""Run coroutines from sync code — safe inside uvicorn/FastAPI event loops."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Awaitable, TypeVar

T = TypeVar("T")


def run_coro_sync(coro: Awaitable[T]) -> T:
    """Execute *coro* and return its result.

    When called from an already-running event loop (e.g. FastAPI ``async def``
    route calling sync ``kernel.execute``), delegates to a worker thread with a
    fresh loop instead of ``asyncio.run()`` which raises RuntimeError.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="cnexus-coro") as pool:
        return pool.submit(asyncio.run, coro).result()
