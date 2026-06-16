"""Prompt execution graph runner v3 — token stream assembly (no string concat path)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.prompt.semantic_delta_v2 import MemoryDeltaAdapter, RuntimeState

ExecutionState = Dict[str, Any]
GraphResult = Dict[str, Any]


class RuntimeContextAdapter:
    """Apply context delta without full snapshot rebuild."""

    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime
        self._state = RuntimeState(runtime)

    def apply_delta(self, context_delta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        snap = self._state.snapshot_light()
        if context_delta:
            state_part = context_delta.get("state_delta") if isinstance(context_delta, dict) else None
            if isinstance(state_part, dict) and state_part.get("values"):
                snap.update(state_part["values"])
        return self._state.diff(snap)


class RuntimeMemoryAdapter:
    """Apply memory diff — hot keys only."""

    def __init__(self, runtime: Optional[Any] = None) -> None:
        self._memory = MemoryDeltaAdapter(runtime)

    def apply_diff(self, context_delta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if isinstance(context_delta, dict) and context_delta.get("memory_delta"):
            return dict(context_delta["memory_delta"])
        fingerprint = self._memory.fingerprint()
        return self._memory.diff(fingerprint)


class RuntimePolicyAdapter:
    """Light non-blocking policy snapshot."""

    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime

    def light_snapshot(self) -> Dict[str, Any]:
        runtime = self.runtime
        if runtime is None:
            return {"risk": "low", "mode": "non_blocking"}
        gov = getattr(runtime, "governance", None)
        policy = getattr(runtime, "policy", None)
        peek = None
        if policy is not None:
            peek = getattr(policy, "light_snapshot", None)
        if peek is None and gov is not None:
            peek = getattr(gov, "peek_non_blocking", None)
        if callable(peek):
            try:
                snapshot = peek()
                if isinstance(snapshot, dict):
                    snapshot.setdefault("mode", "non_blocking")
                    return snapshot
            except Exception:
                pass
        return {"risk": "low", "mode": "non_blocking"}


def ensure_runtime_adapters(runtime: Optional[Any]) -> None:
    """Attach diffable context/policy adapters — never clobber real memory modules."""
    if runtime is None:
        return
    ctx = getattr(runtime, "context", None)
    if not callable(getattr(ctx, "apply_delta", None)):
        runtime.context = RuntimeContextAdapter(runtime)
    pol = getattr(runtime, "policy", None)
    if not callable(getattr(pol, "light_snapshot", None)):
        runtime.policy = RuntimePolicyAdapter(runtime)


class PromptExecutionGraphRunner:
    """Run compiled graph — produces token stream, not assembled string prompt."""

    def __init__(self, runtime: Optional[Any] = None) -> None:
        self.runtime = runtime
        self._context = RuntimeContextAdapter(runtime)
        self._memory = RuntimeMemoryAdapter(runtime)
        self._policy = RuntimePolicyAdapter(runtime)

    def _resolve_context(self, runtime: Optional[Any]) -> RuntimeContextAdapter:
        ctx = getattr(runtime, "context", None) if runtime is not None else None
        if callable(getattr(ctx, "apply_delta", None)):
            return ctx  # type: ignore[return-value]
        return self._context

    def _resolve_memory(self, runtime: Optional[Any]) -> RuntimeMemoryAdapter:
        mem = getattr(runtime, "memory", None) if runtime is not None else None
        if callable(getattr(mem, "apply_diff", None)):
            return mem  # type: ignore[return-value]
        return self._memory

    def _resolve_policy(self, runtime: Optional[Any]) -> RuntimePolicyAdapter:
        pol = getattr(runtime, "policy", None) if runtime is not None else None
        if callable(getattr(pol, "light_snapshot", None)):
            return pol  # type: ignore[return-value]
        return self._policy

    def run(
        self,
        graph: Dict[str, Any],
        runtime: Optional[Any],
        user_input: str,
        context_delta: Optional[Dict[str, Any]] = None,
    ) -> GraphResult:
        effective_runtime = runtime if runtime is not None else self.runtime
        ensure_runtime_adapters(effective_runtime)

        context = self._resolve_context(effective_runtime)
        memory = self._resolve_memory(effective_runtime)
        policy = self._resolve_policy(effective_runtime)
        delta = context_delta if context_delta is not None else graph.get("context_delta") or {}

        state: ExecutionState = {}
        for node in graph.get("nodes") or []:
            op = str(node.get("op") or "")
            if op == "inject_user_input":
                state["input"] = str(user_input)
            elif op == "apply_context_delta":
                state["context"] = context.apply_delta(delta)
            elif op == "apply_memory_diff":
                state["memory"] = memory.apply_diff(delta)
            elif op == "apply_policy_light":
                state["policy"] = policy.light_snapshot()
            elif op == "emit_prompt_tokens":
                state["prompt"] = self._emit(state)

        prompt = state.get("prompt") or self._emit(state)
        return {
            **prompt,
            "mode": "minimal_v3",
            "execution": "compiled_graph",
            "intent": graph.get("intent", "chat"),
        }

    def _emit(self, state: ExecutionState) -> Dict[str, Any]:
        tokens: List[Any] = [
            state.get("input"),
            state.get("context"),
            state.get("memory"),
            state.get("policy"),
        ]
        return {
            "tokens": tokens,
            "text": tokens_to_llm_text(tokens),
        }


def tokens_to_llm_text(tokens: List[Any]) -> str:
    """Fast lane sends user input token only — context stays in graph metadata."""
    for token in tokens:
        if isinstance(token, str) and token.strip():
            return token
    return ""


def get_graph_runner(runtime: Optional[Any] = None) -> PromptExecutionGraphRunner:
    if runtime is not None:
        existing = getattr(runtime, "_prompt_graph_runner_v3", None)
        if isinstance(existing, PromptExecutionGraphRunner):
            return existing
        runner = PromptExecutionGraphRunner(runtime)
        setattr(runtime, "_prompt_graph_runner_v3", runner)
        return runner
    return PromptExecutionGraphRunner(None)
