"""Execution Identity Layer facade."""

from __future__ import annotations

from typing import Any

from core.spine.identity.bundle import build_execution_bundle
from core.spine.identity.equivalence import ReplayEquivalence
from core.spine.identity.kernel import ExecutionIdentityKernel, IDENTITY_VERSION
from core.spine.identity.store import get_identity_store
from core.spine.query.engine import load_spine_rows, query_by_trace
from core.spine.query.index import TraceIndex


class ExecutionIdentityService:
    def __init__(self) -> None:
        self.kernel = ExecutionIdentityKernel()
        self.equivalence = ReplayEquivalence(self.kernel)

    def resolve_for_response(
        self,
        trace_id: str,
        events: list[dict[str, Any]],
        *,
        control: list[dict[str, Any]],
        state: dict[str, Any],
        execution: dict[str, Any],
        base_dir: str | None = None,
        register: bool = True,
    ) -> dict[str, Any]:
        bundle = build_execution_bundle(
            trace_id,
            events,
            control=control,
            state=state,
            execution=execution,
        )
        identity = self.kernel.compute(bundle)
        signatures = self.kernel.signatures(bundle)

        store = get_identity_store()
        if register:
            store.register(identity, trace_id)

        equivalent = [t for t in store.lookup(identity) if t != trace_id]
        drift_variants: list[str] = []

        if base_dir:
            drift_variants = self._find_drift_variants(
                trace_id,
                identity,
                bundle,
                base_dir,
            )

        identity_drift = bool(drift_variants) or any(
            e.get("drift_status") not in (None, "OK") for e in events if isinstance(e, dict)
        )

        return {
            "version": IDENTITY_VERSION,
            "identity": identity,
            "signatures": signatures,
            "equivalent_traces": equivalent,
            "drift_variants": drift_variants,
            "identity_drift": identity_drift,
            "identity_mismatch": identity_drift and bool(drift_variants),
        }

    def _find_drift_variants(
        self,
        trace_id: str,
        identity: str,
        bundle: dict[str, Any],
        base_dir: str,
        *,
        max_traces: int = 50,
    ) -> list[str]:
        """Traces with similar trigger but different identity (drift class)."""
        rows = load_spine_rows(base_dir)
        trace_ids = TraceIndex(rows).trace_ids()[:max_traces]
        graph = bundle.get("graph") or {}
        nodes = graph.get("nodes") or []
        trigger_sig = ""
        if nodes and isinstance(nodes[0], dict):
            trigger_sig = f"{nodes[0].get('phase')}:{nodes[0].get('event_type')}"

        variants: list[str] = []
        for other in trace_ids:
            if other == trace_id:
                continue
            other_events = query_by_trace(base_dir, other, limit=500)
            if not other_events:
                continue
            other_bundle = build_execution_bundle(other, other_events)
            other_id = self.kernel.compute(other_bundle)
            if other_id == identity:
                continue
            other_nodes = (other_bundle.get("graph") or {}).get("nodes") or []
            other_trigger = ""
            if other_nodes and isinstance(other_nodes[0], dict):
                other_trigger = f"{other_nodes[0].get('phase')}:{other_nodes[0].get('event_type')}"
            if trigger_sig and trigger_sig == other_trigger:
                variants.append(other)
        return variants[:10]

    def compare(self, base_dir: str, trace_a: str, trace_b: str) -> dict[str, Any]:
        events_a = query_by_trace(base_dir, trace_a, limit=5000)
        events_b = query_by_trace(base_dir, trace_b, limit=5000)
        from core.spine.query.engine import extract_control, extract_state

        return self.equivalence.compare_traces(
            trace_a,
            events_a,
            trace_b,
            events_b,
            control_a=extract_control(events_a),
            control_b=extract_control(events_b),
            state_a=extract_state(events_a),
            state_b=extract_state(events_b),
        )


def get_identity_service() -> ExecutionIdentityService:
    return ExecutionIdentityService()
