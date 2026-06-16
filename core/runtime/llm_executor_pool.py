"""Dedicated executor pools — LLM fast lane isolated from L3 / governance."""

from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

_llm_executor: Optional[ThreadPoolExecutor] = None
_background_executor: Optional[ThreadPoolExecutor] = None
_lock = threading.Lock()


class ExecutorPool:
    """Resource isolation — LLM lane never shares L3 thread pool."""

    shared_with_l3 = False

    @classmethod
    def llm_executor(cls) -> ThreadPoolExecutor:
        global _llm_executor
        with _lock:
            if _llm_executor is None:
                workers = max(1, min(4, int(os.environ.get("CNEXUS_LLM_FAST_LANE_WORKERS", "2"))))
                _llm_executor = ThreadPoolExecutor(
                    max_workers=workers,
                    thread_name_prefix="cnexus-llm-fast-lane",
                )
            return _llm_executor

    @classmethod
    def background_executor(cls) -> ThreadPoolExecutor:
        global _background_executor
        with _lock:
            if _background_executor is None:
                _background_executor = ThreadPoolExecutor(
                    max_workers=4,
                    thread_name_prefix="cnexus-bg-side-effects",
                )
            return _background_executor


def ensure_runtime_llm_executor(runtime: Optional[object]) -> ThreadPoolExecutor:
    executor = ExecutorPool.llm_executor()
    if runtime is not None:
        setattr(runtime, "llm_executor", executor)
    return executor
