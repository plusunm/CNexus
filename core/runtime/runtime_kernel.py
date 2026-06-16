"""Runtime kernel — passive executor; LLM uses dedicated fast lane."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from core.runtime.llm_executor_pool import ExecutorPool

logger = logging.getLogger(__name__)

_background_executor = ExecutorPool.background_executor()


class RuntimeKernel:
    """Execution backend — offload only, no scheduling semantics."""

    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime

    def offload(self, task: str | Callable[[], Any]) -> None:
        """Always async — never blocks UI / LLM path."""
        if callable(task):
            _background_executor.submit(self._safe_run, task)
            return
        _background_executor.submit(self._run_named, str(task))

    def _safe_run(self, fn: Callable[[], Any]) -> None:
        try:
            fn()
        except Exception as exc:
            logger.debug("RuntimeKernel offload failed: %s", exc)

    def _run_named(self, name: str) -> None:
        try:
            if name in ("embedding.ensure", "embedding.update_hot"):
                self._embedding_ensure()
            elif name in ("memory.recall_hot", "memory.recall_async"):
                self._memory_recall_hot()
            elif name in ("crdt.merge_async", "crdt.merge_lazy"):
                self._crdt_merge_async()
            else:
                logger.debug("RuntimeKernel unknown offload task: %s", name)
        except Exception as exc:
            logger.debug("RuntimeKernel named offload %s failed: %s", name, exc)

    def _embedding_ensure(self) -> None:
        runtime = self.runtime
        if runtime is None:
            return
        mm = getattr(runtime, "memory_manager", None)
        if mm is not None and hasattr(mm, "block_stats"):
            mm.block_stats()

    def _memory_recall_hot(self) -> None:
        runtime = self.runtime
        if runtime is None:
            return
        storage = getattr(runtime, "storage", None)
        if storage is None:
            return
        recall = getattr(storage, "recall", None)
        if callable(recall):
            try:
                recall("", limit=1)
            except TypeError:
                try:
                    recall("")
                except Exception:
                    pass
            except Exception:
                pass

    def _crdt_merge_async(self) -> None:
        try:
            from core.runtime.system_guard import non_hang_v5_enabled

            if not non_hang_v5_enabled():
                return
            from core.kernel.v5.crdt_memory import get_crdt_memory

            get_crdt_memory().stats()
        except Exception:
            pass

    async def llm_generate(self, prompt: str) -> str:
        """Fast lane only — no inference_scheduler / L3 / inline memory."""
        from core.runtime.llm_fast_lane import LLMFastLane, llm_fast_lane_enabled

        if llm_fast_lane_enabled():
            lane = LLMFastLane(self.runtime)
            result = await lane.generate(prompt)
            if isinstance(result, dict):
                return str(result.get("status", "timeout"))
            return str(result)
        return self._llm_generate_legacy(prompt)

    def llm_generate_sync(self, prompt: str) -> str:
        """Direct client chat — bypass scheduler when fast lane is on."""
        from core.runtime.llm_fast_lane import LLMFastLane, llm_fast_lane_enabled

        if llm_fast_lane_enabled():
            lane = LLMFastLane(self.runtime)
            result = lane._call_llm(prompt)
            return str(result)
        return self._llm_generate_legacy(prompt)

    def _llm_generate_legacy(self, prompt: str) -> str:
        runtime = self.runtime
        if runtime is None:
            return f"LLM_RESPONSE:{prompt}"
        llm = getattr(runtime, "llm", None)
        if llm is not None and hasattr(llm, "generate"):
            try:
                result = llm.generate(prompt)
                return str(result)
            except Exception as exc:
                logger.debug("llm_generate fallback: %s", exc)
        chat = getattr(runtime, "chat", None)
        if callable(chat):
            try:
                return str(chat(prompt))
            except Exception:
                pass
        return f"LLM_RESPONSE:{prompt}"

    def cluster_quick_probe(self) -> str:
        try:
            from core.runtime.system_guard import effective_non_hang_tier

            tier = effective_non_hang_tier()
            if tier == "v5":
                from core.kernel.v5.global_cluster_runtime import get_global_cluster_runtime

                return "ok" if get_global_cluster_runtime().cluster_health() else "warming"
            if tier == "v4":
                from core.kernel.v4.cluster_runtime import get_cluster_runtime

                return "ok" if get_cluster_runtime().cluster_healthy() else "warming"
        except Exception:
            pass
        return "deferred"

    def l3_queue_length(self) -> int:
        try:
            from core.runtime.boot_protocol import get_l3_scheduler_status

            l3 = get_l3_scheduler_status() or {}
            return int(l3.get("queue_length") or 0)
        except Exception:
            return 0
