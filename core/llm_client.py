import logging
from typing import List, Optional

from core.execution.inference_scheduler import InferenceScheduler
from core.execution.plane import ExecutionPlane
from core.model_registry import ModelProfile

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified chat client — routes through Inference Scheduler when bound."""

    def __init__(
        self,
        plane: Optional[ExecutionPlane] = None,
        scheduler: Optional[InferenceScheduler] = None,
    ):
        self._plane = plane
        self._scheduler = scheduler

    def bind_scheduler(self, scheduler: InferenceScheduler) -> None:
        self._scheduler = scheduler

    def bind_plane(self, plane: ExecutionPlane) -> None:
        self._plane = plane

    def chat(
        self,
        profile: ModelProfile,
        messages: List[dict],
        temperature: float = 0.7,
        timeout: float = 120.0,
    ) -> str:
        if self._scheduler is not None:
            result = self._scheduler.chat(
                profile,
                messages,
                temperature=temperature,
                timeout=timeout,
            )
            return result.content
        if self._plane is None:
            raise RuntimeError("InferenceScheduler or ExecutionPlane not bound on LLMClient")
        result = self._plane.chat(
            profile,
            messages,
            temperature=temperature,
            timeout=timeout,
        )
        return result.content

    def test_connection(self, profile: ModelProfile) -> tuple[bool, str]:
        try:
            reply = self.chat(
                profile,
                [{"role": "user", "content": "Reply with exactly: OK"}],
                temperature=0,
                timeout=30.0,
            )
            if not reply.strip():
                return False, "模型返回空内容（请检查 model 名称是否为 deepseek-v4-flash）"
            return True, reply[:200]
        except Exception as exc:
            logger.warning("Model test failed: %s", exc)
            return False, str(exc)
