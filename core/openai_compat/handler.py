"""Shared OpenAI-compatible chat completion handler."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from core.llm_client import LLMClient
from core.openai_compat.adapter import MultiLLMAdapter
from core.openai_compat.models import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
)
from core.control_plane.legacy_adapter import LEGACY_OPENAI_CHANNEL
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
    legacy_adapter: Any = None,
) -> ChatCompletionResponse:
    if request.stream:
        raise ValueError("stream=true is not supported yet")

    metadata = dict(request.metadata or {})
    cnexus_extra = metadata.pop("cnexus", None) or request.cnexus
    if isinstance(cnexus_extra, dict):
        metadata.update({k: v for k, v in cnexus_extra.items() if k not in metadata})
    use_memory = bool(metadata.get("use_memory", metadata.get("enable_memory", True)))
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
        "user_id": metadata.get("user_id"),
        "session_id": metadata.get("session_id"),
        "enable_memory": use_memory,
    }
    cnexus_provenance: Dict[str, Any] = {}

    assistant_output = metadata.get("assistant_output")

    if full_cognitive_loop:
        if legacy_adapter is None:
            from core.kernel.enforce.mode import hard_lock_mode

            if hard_lock_mode():
                raise ValueError("kernel execution required: legacy_adapter missing under hard lock")
            result = runtime.process_interaction(
                last_user_msg,
                assistant_output=assistant_output,
                use_memory=use_memory,
                temperature=request.temperature,
                llm_client=llm_client,
                llm_profile=llm_profile,
                allow_proactive=allow_proactive,
            )
        else:
            result = legacy_adapter.interact(
                message=last_user_msg,
                assistant_output=assistant_output,
                use_memory=use_memory,
                temperature=request.temperature,
                llm_client=llm_client,
                llm_profile=llm_profile,
                allow_proactive=allow_proactive,
                metadata=metadata,
                channel=LEGACY_OPENAI_CHANNEL,
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
            cnexus_provenance = {
                "trace_id": result.get("capture_id") or result.get("grounding_event_id"),
                "blocks_used": [],
                "user_id": metadata.get("user_id"),
                "session_id": metadata.get("session_id"),
                "governance": {
                    "values_check": "revised",
                    "cdg_intercept": bool(result.get("cdg")) and not (result.get("cdg") or {}).get(
                        "approved", True
                    ),
                    "revision_note": result.get("reason"),
                },
                "timestamp": datetime.now(timezone.utc).replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        else:
            reply = result.get("reply") or result.get("response", "")
            blocks_used = []
            if result.get("emotion_state"):
                blocks_used.append("emotion")
            if result.get("active_intent"):
                blocks_used.append("intent")
            blocks_used.extend(["persona", "working_memory", "attention_state"])
            cnexus_provenance = {
                "trace_id": result.get("capture_id") or result.get("grounding_event_id"),
                "blocks_used": sorted(set(blocks_used)),
                "user_id": metadata.get("user_id"),
                "session_id": metadata.get("session_id"),
                "governance": {
                    "values_check": "passed",
                    "cdg_intercept": False,
                    "revision_note": None,
                },
                "timestamp": datetime.now(timezone.utc).replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
            }
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

    try:
        trace_id = None
        if cnexus_provenance:
            trace_id = cnexus_provenance.get("trace_id")
        base_dir = str(getattr(runtime, "base_dir", "") or "")
        if trace_id and base_dir:
            from core.spine.token.hooks import emit_tokens_for_llm_usage

            emit_tokens_for_llm_usage(
                str(trace_id),
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                base_dir=base_dir,
                caller="openai_compat",
            )
    except Exception:
        pass

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
        cnexus_provenance=cnexus_provenance or None,
    )


def list_model_cards() -> List[Dict[str, Any]]:
    return [
        {"id": "cnexus-cognitive", "object": "model", "owned_by": "cnexus"},
        {"id": "cnexus-cognitive-pro", "object": "model", "owned_by": "cnexus"},
    ]
