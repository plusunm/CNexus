"""Node executors P_op — state transition functions."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ir_kernel.adapters.runtime_facade import RuntimeFacade
from ir_kernel.policy.cost import step_cost_delta
from ir_kernel.schema.graph import IRNode
from ir_kernel.schema.sigma_exec import SigmaExec, hash_text


@dataclass
class ExecContext:
    use_memory: bool = True
    llm_client: Any = None
    llm_profile: Any = None
    temperature: float = 0.7
    session_meta: Dict[str, Any] = field(default_factory=dict)
    governance_notes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StepOutput:
    value: str
    output_key: str
    extra_variables: Dict[str, str] = field(default_factory=dict)
    latency_ms: int = 0


class NodeExecutor:
    def run(
        self,
        node: IRNode,
        sigma: SigmaExec,
        facade: RuntimeFacade,
        ctx: ExecContext,
    ) -> StepOutput:
        started = time.perf_counter()
        user_message = sigma.variables.get("input", sigma.input.get("user_message", ""))

        if node.op == "INPUT":
            value = user_message
            out_key = node.outputs[0] if node.outputs else "input"
            return self._finish(node, value, out_key, started)

        if node.op == "RETRIEVE":
            if not ctx.use_memory:
                value = ""
                out_key = node.outputs[0] if node.outputs else "context_raw"
                return self._finish(node, value, out_key, started)
            recall = facade.recall_for_ir(user_message, read_only=True)
            sigma.memory_refs.extend(recall.memory_refs)
            out_key = node.outputs[0] if node.outputs else "context_raw"
            return self._finish(node, recall.context, out_key, started)

        if node.op == "FILTER":
            raw = sigma.variables.get("context_raw", "")
            filtered = facade.filter_context(raw)
            out_key = node.outputs[0] if node.outputs else "context"
            return self._finish(node, filtered, out_key, started)

        if node.op == "BUILD_CONTEXT":
            context = sigma.variables.get("context", sigma.variables.get("context_raw", ""))
            bundle = facade.build_outbound(
                user_message,
                context,
                chat_governance_notes=ctx.governance_notes,
            )
            extra = {
                "system_prompt": bundle.system_prompt,
                "governance_injection": bundle.governance_injection,
                "outbound_preview": bundle.outbound_preview,
            }
            out_key = node.outputs[0] if node.outputs else "context"
            return self._finish(
                node,
                context,
                out_key,
                started,
                extra_variables=extra,
            )

        if node.op == "CALL_LLM":
            context = sigma.variables.get("context", "")
            gov = sigma.variables.get("governance_injection", "")
            reply = facade.call_llm(
                user_message,
                context,
                governance_injection=gov,
                llm_client=ctx.llm_client,
                llm_profile=ctx.llm_profile,
                temperature=ctx.temperature,
            )
            out_key = node.outputs[0] if node.outputs else "llm_output"
            return self._finish(node, reply, out_key, started)

        if node.op == "GOVERN":
            raw = sigma.variables.get("llm_output", "")
            gov = facade.govern_output(raw)
            ctx.governance_notes.extend(gov.notes)
            out_key = node.outputs[0] if node.outputs else "reply"
            return self._finish(node, gov.reply, out_key, started)

        if node.op == "REDUCE":
            reply = sigma.variables.get("reply", sigma.variables.get("llm_output", ""))
            facade.enqueue_capture(
                sigma.pending_commits,
                role="user",
                content=user_message,
                meta={"source": "ir_kernel", "trace_id": sigma.trace_id, **ctx.session_meta},
            )
            facade.enqueue_capture(
                sigma.pending_commits,
                role="assistant",
                content=reply,
                meta={"source": "ir_kernel", "trace_id": sigma.trace_id},
            )
            out_key = node.outputs[0] if node.outputs else "final"
            return self._finish(node, reply, out_key, started, extra_variables={"final": reply})

        raise ValueError(f"unsupported_op:{node.op}")

    @staticmethod
    def _finish(
        node: IRNode,
        value: str,
        output_key: str,
        started: float,
        extra_variables: Optional[Dict[str, str]] = None,
    ) -> StepOutput:
        latency_ms = int((time.perf_counter() - started) * 1000)
        extras = dict(extra_variables or {})
        extras[output_key] = value
        return StepOutput(
            value=value,
            output_key=output_key,
            extra_variables=extras,
            latency_ms=latency_ms,
        )
