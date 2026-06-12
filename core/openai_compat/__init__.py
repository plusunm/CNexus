"""OpenAI-compatible API helpers for inbound multi-platform clients."""

from core.openai_compat.adapter import MultiLLMAdapter
from core.openai_compat.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)

__all__ = [
    "MultiLLMAdapter",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "ChatMessage",
]
