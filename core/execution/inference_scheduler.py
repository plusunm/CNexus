"""Adaptive Inference Scheduler — resource policy driven by ComputeProfile."""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, List, Optional

from core.compute_policy import SchedulerPolicy
from core.execution.embed_cache import EmbeddingCache
from core.execution.plane import ExecutionPlane
from core.execution.types import ChatResult, EmbedResult
from core.model_registry import ModelProfile

logger = logging.getLogger(__name__)


class InferenceScheduler:
    """
    Layer 2 control plane: adaptive concurrency, model lock, embed cache-first.
    Policy comes from ComputePolicy — not hardcoded hardware assumptions.
    """

    def __init__(
        self,
        plane: ExecutionPlane,
        *,
        enabled: bool = True,
        cache_enabled: bool = True,
        cache_path: str = "memory/embed_cache.sqlite",
        max_concurrent: int = 1,
        embed_strategy: str = "serial",
        cache_aggressive: bool = True,
    ):
        self.plane = plane
        self.enabled = enabled and max_concurrent > 0
        self.max_concurrent = max(1, int(max_concurrent))
        self.embed_strategy = embed_strategy
        self.cache_aggressive = cache_aggressive
        self._chat_lock = threading.Lock()
        embed_permits = self._embed_permits()
        self._embed_semaphore = threading.BoundedSemaphore(embed_permits)
        self._active_model: Optional[str] = None
        self._cache = EmbeddingCache(cache_path) if cache_enabled else None
        self._stats: Dict[str, int] = {
            "chat_executed": 0,
            "embed_executed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "serial_waits": 0,
        }

    def _embed_permits(self) -> int:
        if self.embed_strategy == "serial":
            return 1
        if self.embed_strategy == "parallel_limited":
            return max(1, min(self.max_concurrent, 2))
        return max(1, self.max_concurrent)

    @classmethod
    def from_config(cls, plane: ExecutionPlane, cfg: Dict[str, Any], *, base_dir: str) -> "InferenceScheduler":
        cache_path = cfg.get("embedding_cache_path") or str(
            __import__("pathlib").Path(base_dir) / "embed_cache.sqlite"
        )
        policy_raw = (cfg.get("compute_policy") or {}).get("scheduler") or {}
        scheduler_policy = SchedulerPolicy(
            enabled=bool(cfg.get("inference_scheduler_enabled", policy_raw.get("enabled", True))),
            max_concurrency=int(cfg.get("inference_max_concurrent", policy_raw.get("max_concurrency", 1))),
            embed_strategy=str(policy_raw.get("embed_strategy") or "serial"),
            cache_aggressive=bool(policy_raw.get("cache_aggressive", True)),
        )
        enabled = scheduler_policy.enabled
        if os.environ.get("CNEXUS_INFERENCE_SCHEDULER", "").lower() in ("0", "false", "no"):
            enabled = False
        cache_enabled = bool(cfg.get("embedding_cache_enabled", True))
        if scheduler_policy.cache_aggressive:
            cache_enabled = True
        return cls(
            plane,
            enabled=enabled,
            cache_enabled=cache_enabled,
            cache_path=str(cache_path),
            max_concurrent=scheduler_policy.max_concurrency,
            embed_strategy=scheduler_policy.embed_strategy,
            cache_aggressive=scheduler_policy.cache_aggressive,
        )

    def stats_payload(self) -> Dict[str, Any]:
        payload = {
            "enabled": self.enabled,
            "max_concurrent": self.max_concurrent,
            "embed_strategy": self.embed_strategy,
            "cache_aggressive": self.cache_aggressive,
            "active_model": self._active_model,
            **self._stats,
        }
        if self._cache:
            payload["cache"] = self._cache.stats()
        return payload

    def chat(
        self,
        profile: ModelProfile,
        messages: List[dict],
        *,
        temperature: float = 0.7,
        timeout: float = 120.0,
    ) -> ChatResult:
        effective_timeout = self._effective_chat_timeout(timeout)
        if not self.enabled or profile.provider != "ollama":
            return self.plane.chat(
                profile,
                messages,
                temperature=temperature,
                timeout=effective_timeout,
            )

        def _run() -> ChatResult:
            self._ensure_model(profile.model)
            return self.plane.chat(
                profile,
                messages,
                temperature=temperature,
                timeout=effective_timeout,
            )

        result = self._run_chat_exclusive(_run)
        self._stats["chat_executed"] += 1
        return result

    @staticmethod
    def _effective_chat_timeout(requested: float) -> float:
        raw = os.environ.get("CNEXUS_NON_HANG_INFERENCE_TIMEOUT_SEC", "").strip()
        if not raw:
            return requested
        try:
            cap = float(raw)
        except ValueError:
            return requested
        return min(requested, max(1.0, cap))

    def embed(self, text: str, *, model: Optional[str] = None) -> EmbedResult:
        embed_model = model or self.plane.embed_model

        if self._cache:
            cached = self._cache.get(text, embed_model)
            if cached is not None:
                self._stats["cache_hits"] += 1
                return EmbedResult(vector=cached, provider="cache", model=embed_model)

        self._stats["cache_misses"] += 1

        force_hash = os.environ.get("BM_EMBEDDING_MODE", "auto").lower() == "hash"
        if not self.enabled or force_hash:
            result = self.plane.embed(text, model=embed_model)
        else:

            def _run() -> EmbedResult:
                self._ensure_model(embed_model)
                return self.plane.embed(text, model=embed_model)

            result = self._run_embed(_run)
            self._stats["embed_executed"] += 1

        if self._cache and result.vector:
            self._cache.set(text, embed_model, list(result.vector))
        return result

    def _ensure_model(self, model: str) -> None:
        if self._active_model == model:
            return
        if self._active_model is not None:
            logger.debug("InferenceScheduler model swap: %s -> %s", self._active_model, model)
        self._active_model = model

    def _run_chat_exclusive(self, fn):
        self._stats["serial_waits"] += 1
        with self._chat_lock:
            return fn()

    def _run_embed(self, fn):
        self._stats["serial_waits"] += 1
        with self._embed_semaphore:
            return fn()

    @staticmethod
    async def run_bounded_coro(coro, *, timeout_s: float = 8.0):
        """Optional async helper for callers on the event loop (Non-Hang v2)."""
        import asyncio

        try:
            return await asyncio.wait_for(coro, timeout=timeout_s)
        except asyncio.TimeoutError:
            return {"status": "timeout"}
