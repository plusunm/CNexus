"""Shared OpenAI-compatible chat completion handler."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from core.llm_client import LLMClient
from core.openai_compat.adapter import MultiLLMAdapter
from core.openai_compat.models import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)
from core.skill.skill_registry import SkillRegistry


def _messages_to_dicts(messages: List[ChatMessage]) -> List[Dict[str, str]]:
    payload: List[Dict[str, str]] = []
    for message in messages:
        if message.content:
            payload.append({"role": message.role, "content": message.content})
    return payload


def _extract_last_user_message(messages: List[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user" and message.content:
            return message.content.strip()
    return ""


def _estimate_usage(prompt: str, completion: str) -> Dict[str, int]:
    prompt_tokens = max(1, len(prompt) // 4)
    completion_tokens = max(1, len(completion) // 4)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


async def _maybe_execute_tool_calls(
    messages: List[ChatMessage],
    skills: SkillRegistry,
) -> Optional[str]:
    """If the latest assistant message requests tools, execute and return tool output."""
    last_assistant: Optional[ChatMessage] = None
    for message in reversed(messages):
        if message.role == "assistant":
            last_assistant = message
            break
    if not last_assistant or not last_assistant.tool_calls:
        return None

    outputs: List[str] = []
    for call in last_assistant.tool_calls:
        fn = (call or {}).get("function") or {}
        name = fn.get("name")
        if not name:
            continue
        result = await skills.execute_tool_call(name, fn.get("arguments", "{}"))
        outputs.append(result)
    return "\n".join(outputs) if outputs else None


async def create_chat_completion(
    request: ChatCompletionRequest,
    *,
    runtime: Any,
    registry: Any,
    llm_client: LLMClient,
    skills: SkillRegistry,
) -> ChatCompletionResponse:
    if request.stream:
        raise ValueError("stream=true is not supported yet")

    metadata = dict(request.metadata or {})
    use_memory = bool(metadata.get("use_memory", True))
    allow_proactive = bool(metadata.get("allow_proactive", True))
    full_cognitive_loop = bool(metadata.get("full_cognitive_loop", True))

    last_user_msg = _extract_last_user_message(request.messages)
    if not last_user_msg:
        raise ValueError("messages must include at least one user message")

    adapter = MultiLLMAdapter(runtime, registry, llm_client)
    llm_profile = adapter.resolve_profile(request.model)

    tool_output = await _maybe_execute_tool_calls(request.messages, skills)
    if tool_output:
        last_user_msg = (
            f"{last_user_msg}\n\n[Tool Results]\n{tool_output}"
            if last_user_msg
            else tool_output
        )

    cnexus_meta: Dict[str, Any] = {
        "full_cognitive_loop": full_cognitive_loop,
        "model_profile": llm_profile.model,
        "provider": llm_profile.provider,
    }

    assistant_output = metadata.get("assistant_output")

    if full_cognitive_loop:
        result = runtime.process_interaction(
            last_user_msg,
            assistant_output=assistant_output,
            use_memory=use_memory,
            temperature=request.temperature,
            llm_client=llm_client,
            llm_profile=llm_profile,
            allow_proactive=allow_proactive,
        )
        if not result.get("ok", True):
            reply = result.get("reply") or result.get("response", "")
            cnexus_meta.update(
                {
                    "ok": False,
                    "reason": result.get("reason"),
                    "coherence_score": result.get("coherence_score"),
                }
            )
        else:
            reply = result.get("reply") or result.get("response", "")
            cnexus_meta.update(
                {
                    "ok": True,
                    "coherence_score": result.get("coherence_score"),
                    "meta_reflection": result.get("meta_reflection"),
                    "emotion_state": result.get("emotion_state"),
                    "active_intent": result.get("active_intent"),
                    "value_alignment": result.get("value_alignment"),
                    "proactive": result.get("proactive"),
                }
            )
    else:
        reply = await adapter.generate(
            _messages_to_dicts(request.messages),
            request.model,
            temperature=request.temperature,
        )
        cnexus_meta["ok"] = True

    usage = _estimate_usage(last_user_msg, reply)
    return ChatCompletionResponse(
        model=request.model,
        choices=[
            ChatCompletionChoice(
                message=ChatMessage(role="assistant", content=reply),
                finish_reason="stop",
            )
        ],
        usage=usage,
        cnexus=cnexus_meta,
    )


def list_model_cards() -> List[Dict[str, Any]]:
    return [
        {"id": "cnexus-cognitive", "object": "model", "owned_by": "cnexus"},
        {"id": "cnexus-cognitive-pro", "object": "model", "owned_by": "cnexus"},
    ]
