"""Thin entry dispatcher — routes HTTP/WS write paths through entry_registry checks."""



from __future__ import annotations



import os

from typing import Any, Dict, Optional, TYPE_CHECKING



from core.control_plane.audit import audit_decision

from core.control_plane.decision_engine import DecisionEngine

from core.control_plane.exceptions import ControlDecisionRejected

from core.control_plane.guards import dispatch_context

from core.control_plane.registry import (

    EntryNotRegisteredError,

    enforce_route_entry,

    resolve_registry_entry,

)

from core.control_plane.types import DispatchContext, RouteKind, build_dispatch_context

from core.runtime.trace_context import trace_scope



if TYPE_CHECKING:

    from brain_memory.runtime import BrainMemoryRuntime





def _hard_gate_enabled() -> bool:

    return os.environ.get("CONTROL_PLANE_HARD_GATE", "").strip().lower() in (

        "1",

        "true",

        "yes",

    )





class AuthorityDispatcher:

    """Phase 0 forwarder + Phase 1 decision overlay (default: observe-only)."""



    def __init__(self, runtime: "BrainMemoryRuntime"):

        self.runtime = runtime

        self._decision_engine = DecisionEngine()

        from core.kernel.migration.patch_runtime import create_kernel_for
        from core.kernel.migration.runtime_proxy import RuntimeProxy

        if isinstance(runtime, RuntimeProxy):
            self._kernel = runtime.kernel
        else:
            self._kernel = create_kernel_for(runtime)



    def dispatch(self, ctx: DispatchContext) -> Any:

        seed = ctx.trace_id or ctx.payload.get("trace_id")

        with trace_scope(seed if isinstance(seed, str) else None) as active_trace:

            ctx.trace_id = active_trace

            try:

                registry_entry = resolve_registry_entry(ctx.kind.value)

                spec = enforce_route_entry(ctx.kind.value)

            except EntryNotRegisteredError:

                decision = DecisionEngine.unknown_entry(ctx)

                audit_decision(decision, trace_id=ctx.trace_id)

                if decision.blocks_when_hard_gate() and _hard_gate_enabled():

                    raise ControlDecisionRejected(decision)

                raise

            from core.spine.emit import emit_dispatch

            emit_dispatch(kind=ctx.kind.value, entry=registry_entry, trace_id=ctx.trace_id)

            decision = self._decision_engine.decide(

                ctx,

                registry_entry=registry_entry,

                spec=spec,

            )

            audit_decision(

                decision,

                trace_id=ctx.trace_id,

                extra=self._audit_extra(ctx, spec),

            )

            if decision.blocks_when_hard_gate() and _hard_gate_enabled():

                raise ControlDecisionRejected(decision)



            with dispatch_context():
                from core.governance.gtbs.write_intent_bus import write_intent_provenance_scope

                with write_intent_provenance_scope(
                    trace_id=ctx.trace_id,
                    dispatch_kind=ctx.kind.value,
                    caller=ctx.caller,
                    channel=ctx.channel,
                    entry_registry=registry_entry,
                ):
                    result = self._execute(ctx)
                    if isinstance(result, dict) and ctx.trace_id:
                        result.setdefault("trace_id", ctx.trace_id)
                    return result



    @staticmethod

    def _audit_extra(ctx: DispatchContext, spec: Dict[str, Any]) -> Dict[str, Any]:

        extra: Dict[str, Any] = {}

        if ctx.kind is RouteKind.IR_EXECUTE:

            commit = ctx.payload.get("commit", True)

            extra["commit"] = commit

            extra["read_only"] = not commit

        if ctx.kind is RouteKind.MEMORY_READ:

            extra["mutate_state"] = False

        if ctx.kind is RouteKind.OBSERVE_READ:

            extra["mutate_state"] = False

            extra["read_only"] = True

        if spec.get("deprecated_for_external"):

            extra["deprecated_for_external"] = True

        return extra



    def _execute(self, ctx: DispatchContext) -> Any:

        from core.kernel.enforce.gate import get_enforce_gate
        from core.kernel.enforce.mode import execution_via_kernel_required, hard_lock_mode, legacy_allowed
        from core.kernel.intent import dispatch_context_to_intent

        gate = get_enforce_gate()

        if execution_via_kernel_required():
            intent = dispatch_context_to_intent(ctx)
            record = self._kernel.execute(intent)
            return record.to_legacy_response()

        if hard_lock_mode() or not legacy_allowed():
            gate.block_legacy_route(ctx.kind.value)

        return self._execute_legacy(ctx)

    def _execute_legacy(self, ctx: DispatchContext) -> Any:

        from core.kernel.enforce.gate import get_enforce_gate
        from core.kernel.enforce.mode import hard_lock_mode, legacy_allowed

        if hard_lock_mode() or not legacy_allowed():
            get_enforce_gate().block_legacy_route(ctx.kind.value)

        kind = ctx.kind
        p = ctx.payload



        if kind in (RouteKind.CHAT_SEND, RouteKind.WS_CHAT):

            return self.runtime.process_interaction(

                p["message"],

                use_memory=p.get("use_memory", True),

                temperature=p.get("temperature", 0.7),

                llm_client=p.get("llm_client"),

                llm_profile=p.get("llm_profile"),

                allow_proactive=p.get("allow_proactive", True),

                chat_mode=p.get("chat_mode", True),

                metadata=p.get("metadata"),

                assistant_output=p.get("assistant_output"),

                user_id=p.get("user_id"),

            )



        if kind == RouteKind.CHAT_PREPARE:

            return self.runtime.prepare_chat_turn(

                p["message"],

                use_memory=p.get("use_memory", True),

                chat_mode=p.get("chat_mode", True),

                metadata=p.get("metadata"),

            )



        if kind == RouteKind.CHAT_CONFIRM:

            return self.runtime.confirm_prepared_chat_turn(

                p["prepare_id"],

                temperature=p.get("temperature", 0.7),

                llm_client=p.get("llm_client"),

                llm_profile=p.get("llm_profile"),

                allow_proactive=p.get("allow_proactive", True),

                send_mode=p.get("send_mode"),

            )



        if kind == RouteKind.CHAT_CANCEL:

            return self.runtime.cancel_prepared_chat_turn(p["prepare_id"])



        if kind == RouteKind.MEMORY_READ:

            return self.runtime.recall(

                p["query"],

                top_k=p.get("top_k"),

                use_attention=p.get("use_attention", True),

                mutate_state=False,

            )



        if kind == RouteKind.MEMORY_WRITE:

            return self.runtime.capture(

                p["role"],

                p["content"],

                layer=p.get("layer", "episodic"),

                importance=p.get("importance", 0.5),

                **p.get("meta", {}),

            )



        if kind == RouteKind.GOVERNANCE_CYCLE:

            return self.runtime.run_governance_cycle()



        if kind == RouteKind.IR_COMPILE:

            from ir_kernel.engine import compile_graph



            return compile_graph(

                p["message"],

                template=p.get("template", "chat_single_turn"),

                use_memory=p.get("use_memory", True),

            )



        if kind == RouteKind.IR_EXECUTE:

            from ir_kernel.engine import compile_and_execute

            from ir_kernel.adapters.runtime_facade import RuntimeFacade

            from ir_kernel.runtime.executor import ExecContext



            facade = RuntimeFacade(self.runtime)

            exec_ctx = ExecContext(

                use_memory=p.get("use_memory", True),

                llm_client=p["llm_client"],

                llm_profile=p["llm_profile"],

                temperature=p.get("temperature", 0.7),

                session_meta=p.get("session_meta") or {},

            )

            return compile_and_execute(

                p["message"],

                facade,

                template=p.get("template", "chat_single_turn"),

                use_memory=p.get("use_memory", True),

                ctx=exec_ctx,

                commit=p.get("commit", True),

            )



        raise ValueError(f"unsupported dispatch kind: {kind}")



    def _dispatch_payload(

        self,

        kind: RouteKind,

        payload: Dict[str, Any],

        *,

        caller: str = "http",

        channel: str = "brain-memory-ui",

        trace_id: Optional[str] = None,

    ) -> Any:

        effective_trace = trace_id or payload.get("trace_id")

        return self.dispatch(

            build_dispatch_context(

                kind,

                payload,

                caller=caller,

                channel=channel,

                trace_id=effective_trace if isinstance(effective_trace, str) else None,

            )

        )



    # Convenience wrappers for routes

    def chat_send(self, **payload: Any) -> Any:

        return self._dispatch_payload(RouteKind.CHAT_SEND, payload)



    def chat_prepare(self, **payload: Any) -> Any:

        return self._dispatch_payload(RouteKind.CHAT_PREPARE, payload)



    def chat_confirm(
        self,
        prepare_id: str,
        *,
        temperature: float = 0.7,
        llm_client: Any = None,
        llm_profile: Any = None,
        allow_proactive: bool = True,
        send_mode: Any = None,
        **extra: Any,
    ) -> Any:
        payload: Dict[str, Any] = {
            "prepare_id": prepare_id,
            "temperature": temperature,
            "llm_client": llm_client,
            "llm_profile": llm_profile,
            "allow_proactive": allow_proactive,
            "send_mode": send_mode,
        }
        if extra:
            payload.update(extra)
        return self._dispatch_payload(RouteKind.CHAT_CONFIRM, payload)



    def chat_cancel(self, prepare_id: str) -> bool:

        return self._dispatch_payload(

            RouteKind.CHAT_CANCEL,

            {"prepare_id": prepare_id},

        )



    def memory_recall(self, query: str, *, top_k: Optional[int] = None) -> str:

        return self._dispatch_payload(

            RouteKind.MEMORY_READ,

            {"query": query, "top_k": top_k},

        )



    def memory_capture(

        self,

        role: str,

        content: str,

        *,

        layer: str = "episodic",

        importance: float = 0.5,

        meta: Optional[Dict[str, Any]] = None,

    ) -> Any:

        return self._dispatch_payload(

            RouteKind.MEMORY_WRITE,

            {

                "role": role,

                "content": content,

                "layer": layer,

                "importance": importance,

                "meta": meta or {},

            },

        )



    def governance_cycle(self) -> Dict[str, Any]:

        return self._dispatch_payload(RouteKind.GOVERNANCE_CYCLE, {})



    def ir_execute(self, **payload: Any) -> Any:

        return self._dispatch_payload(RouteKind.IR_EXECUTE, payload)



    def ws_chat(self, **payload: Any) -> Any:

        return self._dispatch_payload(

            RouteKind.WS_CHAT,

            payload,

            caller="websocket",

        )

    def memory_maintenance(self, *, force: bool = False) -> Any:
        return self._dispatch_payload(RouteKind.MEMORY_MAINTENANCE, {"force": force})

    def capture_cognition(
        self,
        *,
        content: str,
        layer: str = "episodic",
        memory_id: Optional[str] = None,
        trigger_governance: Optional[bool] = None,
    ) -> Any:
        return self._dispatch_payload(
            RouteKind.CAPTURE_COGNITION,
            {
                "content": content,
                "layer": layer,
                "memory_id": memory_id,
                "trigger_governance": trigger_governance,
            },
        )

    def reflect_review(
        self,
        *,
        content: str,
        traits: Optional[list] = None,
        trigger_governance: bool = True,
    ) -> Any:
        return self._dispatch_payload(
            RouteKind.REFLECT_REVIEW,
            {"content": content, "traits": traits, "trigger_governance": trigger_governance},
        )

    def reflect_due_reviews(self) -> Any:
        return self._dispatch_payload(RouteKind.REFLECT_DUE_REVIEWS, {})

    def governance_validate(self, *, days: int = 30) -> Any:
        return self._dispatch_payload(RouteKind.GOVERNANCE_VALIDATE, {"days": days})

    def observe_read(self, kind: str, **payload: Any) -> Any:
        body = dict(payload)
        body["kind"] = kind
        return self._dispatch_payload(RouteKind.OBSERVE_READ, body)


