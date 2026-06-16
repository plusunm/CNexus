"""Delta-only async enrichment v2 — skip unchanged memory/state."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from core.prompt.context_enhancer_v1 import (
    enrich_prompt_async,
    schedule_layer2_background,
)
from core.prompt.minimal_builder_v1 import PromptDict
from core.runtime.async_bridge import run_coro_sync

logger = logging.getLogger(__name__)


def _has_delta_changes(delta_prompt: PromptDict) -> bool:
    state_delta = delta_prompt.get("state_delta") or {}
    memory_delta = delta_prompt.get("memory_delta") or {}
    if memory_delta.get("changed"):
        return True
    if state_delta.get("has_changes") or state_delta.get("changed_keys"):
        return True
    return False


def schedule_delta_enrichment(runtime: Optional[Any], delta_prompt: PromptDict) -> None:
    """Enrich only when state/memory deltas changed — else Layer-2 only."""

    if _has_delta_changes(delta_prompt):

        async def _run() -> None:
            try:
                await enrich_prompt_async(runtime, delta_prompt)
            except Exception as exc:
                logger.debug("schedule_delta_enrichment failed: %s", exc)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_run())
        except RuntimeError:
            run_coro_sync(enrich_prompt_async(runtime, delta_prompt))
        return

    schedule_layer2_background(runtime, delta_prompt)
