"""ExecutionKernel — CP-3 single entry: kernel.execute(intent) → ExecutionRecord."""

from __future__ import annotations

import os
from typing import Any, TYPE_CHECKING

from core.kernel.context import ExecutionContext
from core.kernel.hooks import (
    after_execute,
    after_graph,
    before_execute,
    before_graph,
    record_execution_tap,
    resolve_identity,
)
from core.kernel.intent import ExecutionIntent
from core.kernel.record import ExecutionRecord, LazyExecutionRecord
from core.kernel.router import route_intent
from core.kernel.tier.fast_path import execute_fast_chat
from core.kernel.tier.minimal_path import execute_minimal
from core.kernel.tier.resolver import resolve_execution_tier
from core.runtime.trace_context import start_trace

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime
    from core.kernel.graph.execution_graph import KernelExecutionGraph


def kernel_enabled() -> bool:
    flag = os.environ.get("USE_EXECUTION_KERNEL", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def graph_enabled() -> bool:
    flag = os.environ.get("USE_EXECUTION_GRAPH", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


class ExecutionKernel:
    """Single execution entry — produces ExecutionRecord as sole truth."""

    def __init__(self, runtime: "BrainMemoryRuntime") -> None:
        self.runtime = runtime
        from core.kernel.graph.builder import GraphBuilder
        from core.kernel.graph.scheduler import GraphScheduler
        from core.kernel.graph.scheduler_v2 import SchedulerV2, scheduler_v2_enabled
        from core.kernel.identity.index_v1 import get_identity_graph_index
        from core.kernel.replay.engine_v1 import ExecutionGraphReplayEngineV1

        self._builder = GraphBuilder()
        self._scheduler_v1 = GraphScheduler()
        self._scheduler_v2 = SchedulerV2()
        self._use_scheduler_v2 = scheduler_v2_enabled
        self._identity_index = get_identity_graph_index()
        self._replay_engine = ExecutionGraphReplayEngineV1(
            self._scheduler_v2,
            self._identity_index,
            runtime,
        )
        self._records: dict[str, ExecutionRecord] = {}
        from core.kernel.observe.record_store import KernelRecordStore

        self._record_store = KernelRecordStore(str(runtime.base_dir))
        self._hydrate_records()

    def _hydrate_records(self, *, limit: int = 120) -> None:
        for trace_id in self._record_store.list_trace_ids(limit=limit):
            if trace_id in self._records:
                continue
            data = self._record_store.get(trace_id)
            if not data:
                continue
            try:
                self._records[trace_id] = ExecutionRecord.from_dict(data)
            except Exception:
                continue

    def _persist_record(self, record: ExecutionRecord) -> None:
        try:
            self._record_store.append(record.to_dict())
        except Exception:
            pass
        self._emit_evolved_observability(record)

    def _emit_evolved_observability(self, record: ExecutionRecord) -> None:
        try:
            from core.evolved.trace_emit import emit_sigma_trace

            emit_sigma_trace(str(self.runtime.base_dir), record)
        except Exception:
            pass
        try:
            from core.evolved.cognitive_hooks import dispatch_cognitive_step
            from core.evolved.store_step import build_store_projection, is_store_intent

            store = getattr(self.runtime, "self_model_store", None)
            if store is None:
                return
            store_proj = build_store_projection(record) if is_store_intent(record.intent_type) else None
            dispatch_cognitive_step(
                store,
                record.intent_type,
                block_updated_at=(store_proj or {}).get("block_updated_at"),
            )
        except Exception:
            pass

    def _store_record(self, trace_id: str, record: ExecutionRecord) -> ExecutionRecord:
        self._records[trace_id] = record
        self._persist_record(record)
        return record

    def new_trace_id(self, explicit: str | None = None) -> str:
        return start_trace(explicit)

    def execute(self, intent: ExecutionIntent) -> ExecutionRecord:
        from core.kernel.enforce.gate import get_enforce_gate

        gate = get_enforce_gate()
        with gate.execution_scope(intent):
            record = self._execute_inner(intent)
            gate.validate_record(record)
            return record

    def _execute_inner(self, intent: ExecutionIntent) -> ExecutionRecord:
        trace_id = (intent.trace_id or "").strip() or self.new_trace_id()
        start_trace(trace_id)

        ctx = ExecutionContext(
            trace_id=trace_id,
            identity_id=resolve_identity(trace_id),
            tags={"source": intent.source, "intent": intent.type},
        )

        tier = resolve_execution_tier(intent, ctx)
        ctx.meta["execution_tier"] = tier
        ctx.tags["execution_tier"] = tier

        record_execution_tap(
            {
                "trace_id": trace_id,
                "intent": intent.type,
                "phase": "enter_kernel",
                "source": intent.source,
                "execution_tier": tier,
            }
        )
        before_execute(intent, ctx, tier=tier)

        if tier == "T0":
            result = execute_fast_chat(intent, ctx, self.runtime)
            after_execute(intent, ctx, result, tier=tier)
            record = LazyExecutionRecord.materialize_lazy(
                intent=intent,
                ctx=ctx,
                result=result,
                tier=tier,
            )
            return self._store_record(trace_id, record)

        if tier == "T1":
            result = execute_minimal(intent, ctx, self.runtime)
            after_execute(intent, ctx, result, tier=tier)
            record = LazyExecutionRecord.materialize_lazy(
                intent=intent,
                ctx=ctx,
                result=result,
                tier=tier,
            )
            return self._store_record(trace_id, record)

        if tier == "T2":
            result = route_intent(intent, ctx, self.runtime)
            after_execute(intent, ctx, result, tier=tier)
            record = LazyExecutionRecord.materialize_lazy(
                intent=intent,
                ctx=ctx,
                result=result,
                tier=tier,
            )
            return self._store_record(trace_id, record)

        graph = None
        identity_info: dict[str, Any] | None = None

        if graph_enabled():
            graph = self._builder.build(intent, trace_id, tier=tier)
            before_graph(graph, ctx, tier=tier)
            if self._use_scheduler_v2():
                result = self._scheduler_v2.run(graph, ctx, self.runtime)
            else:
                result = self._scheduler_v1.run(graph, ctx, self.runtime)

            identity_info = self._resolve_graph_identity(graph, trace_id)
            identity_info["execution_tier"] = tier
            ctx.identity_id = identity_info["identity"]
            record_execution_tap(
                {
                    "trace_id": trace_id,
                    "phase": "identity_indexed",
                    "execution_tier": tier,
                    "identity": identity_info["identity"],
                    "equivalent_count": identity_info["equivalence"]["count"],
                }
            )
            result = self._attach_identity(result, identity_info, trace_id)
            after_graph(graph, ctx, result, tier=tier)
        else:
            result = route_intent(intent, ctx, self.runtime)
            after_execute(intent, ctx, result, tier=tier)
            record_execution_tap(
                {
                    "trace_id": trace_id,
                    "intent": intent.type,
                    "phase": "exit_kernel",
                    "execution_tier": tier,
                    "result_type": type(result).__name__,
                    "elapsed_ms": ctx.elapsed_ms(),
                }
            )

        record = ExecutionRecord.materialize(
            intent=intent,
            ctx=ctx,
            result=result,
            graph=graph,
            identity_info=identity_info,
        )
        return self._store_record(trace_id, record)

    def replay(
        self,
        graph: "KernelExecutionGraph | None" = None,
        *,
        trace_id: str | None = None,
        record: ExecutionRecord | None = None,
        verify_identity: bool = True,
    ) -> dict[str, Any]:
        from core.kernel.enforce.context import kernel_execution_context

        with kernel_execution_context(source="replay"):
            if record is not None:
                return self._replay_engine.replay_record(record, verify_identity=verify_identity)
            if trace_id:
                stored = self.get_record(trace_id)
                if stored is not None:
                    return self._replay_engine.replay_record(
                        stored,
                        verify_identity=verify_identity,
                    )
            if graph is not None:
                return self._replay_engine.replay(
                    graph,
                    trace_id=trace_id,
                    verify_identity=verify_identity,
                )
            raise ValueError("replay requires graph, trace_id with stored record, or ExecutionRecord")

    def get_record(self, trace_id: str) -> ExecutionRecord | None:
        record = self._records.get(trace_id)
        if record is not None:
            return record
        data = self._record_store.get(trace_id)
        if not data:
            return None
        try:
            record = ExecutionRecord.from_dict(data)
        except Exception:
            return None
        self._records[trace_id] = record
        return record

    def list_record_ids(self, *, limit: int = 40) -> list[str]:
        if limit <= 0:
            return []
        merged: list[str] = []
        seen: set[str] = set()
        for tid in list(self._records.keys()) + self._record_store.list_trace_ids(limit=limit * 2):
            if tid and tid not in seen:
                seen.add(tid)
                merged.append(tid)
        return merged[-limit:]

    def _resolve_graph_identity(self, graph: Any, trace_id: str) -> dict[str, Any]:
        identity = self._identity_index.register(trace_id, graph)
        equivalence = self._identity_index.find_equivalent_traces(graph, exclude_trace=trace_id)
        return {"identity": identity, "equivalence": equivalence}

    def _attach_identity(self, result: Any, identity_info: dict[str, Any], trace_id: str) -> Any:
        if isinstance(result, dict):
            merged = dict(result)
            merged.setdefault("identity", identity_info["identity"])
            merged.setdefault("equivalence", identity_info["equivalence"])
            merged.setdefault("trace_id", trace_id)
            return merged
        return result
