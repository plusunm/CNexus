"""Runtime method → ExecutionIntent mapping."""

from __future__ import annotations

from typing import Any

from core.kernel.intent import ExecutionIntent
from core.kernel.migration.auto_wrap import strip_kernel_flags


def map_runtime_call(
    method_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    source: str = "runtime_proxy",
) -> ExecutionIntent:
    clean = strip_kernel_flags(kwargs)

    if method_name in ("chat_send", "process_interaction"):
        message = args[0] if args else clean.pop("message", "")
        return ExecutionIntent(
            type="chat",
            payload={"message": message, **clean},
            trace_id=clean.pop("trace_id", None),
            source=source,
        )

    if method_name == "prepare_chat_turn":
        message = args[0] if args else clean.pop("message", "")
        return ExecutionIntent(
            type="chat",
            payload={"message": message, "_action": "prepare", **clean},
            source=source,
        )

    if method_name == "confirm_prepared_chat_turn":
        prepare_id = args[0] if args else clean.pop("prepare_id", "")
        return ExecutionIntent(
            type="chat",
            payload={"prepare_id": prepare_id, "_action": "confirm", **clean},
            source=source,
        )

    if method_name == "cancel_prepared_chat_turn":
        prepare_id = args[0] if args else clean.pop("prepare_id", "")
        return ExecutionIntent(
            type="chat",
            payload={"prepare_id": prepare_id, "_action": "cancel", **clean},
            source=source,
        )

    if method_name == "recall":
        query = args[0] if args else clean.pop("query", "")
        return ExecutionIntent(
            type="recall",
            payload={"query": query, **clean},
            source=source,
        )

    if method_name == "capture":
        if len(args) >= 2:
            role, content = args[0], args[1]
            payload = {"role": role, "content": content, **clean}
        else:
            payload = dict(clean)
        return ExecutionIntent(
            type="capture",
            payload=payload,
            source=source,
        )

    if method_name in ("run_governance_cycle", "cdg_apply", "cdg_ingest", "control"):
        return ExecutionIntent(
            type="cdg_apply",
            payload=clean,
            source=source,
        )

    if method_name == "ir_execute":
        return ExecutionIntent(
            type="ir_exec",
            payload=clean if not args else {"message": args[0], **clean},
            source=source,
        )

    return ExecutionIntent(
        type="system",
        payload={
            "_runtime_method": method_name,
            "args": args,
            "kwargs": clean,
        },
        source=source,
    )
