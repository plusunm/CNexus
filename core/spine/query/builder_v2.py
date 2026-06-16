"""Drift-aware Spine Query Engine v2."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from core.runtime.execution_tap import get_execution_tap
from core.spine.drift.annotator import DriftAnnotator
from core.spine.drift.detector import RuntimeSpineDriftDetector
from core.spine.execution.bind_v2 import bind_explanation_to_execution_v2
from core.spine.execution.builder import build_execution_graph
from core.spine.healing.repair import SpineHealer
from core.spine.query.builder import run_parsed_query
from core.spine.query.engine import query_by_trace
from core.spine.query.types import SpineQueryResponse

SCHEMA_VERSION_V2 = "spine-query-2"

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def run_query_v2(
    base_dir: str,
    *,
    query: str | None = None,
    trace_id: str | None = None,
    mode: str = "causal",
    limit: int = 200,
    runtime: Optional["BrainMemoryRuntime"] = None,
) -> SpineQueryResponse:
    from core.spine.query.builder import run_query

    v1 = run_query(base_dir, query=query, trace_id=trace_id, mode=mode, limit=limit)
    return enrich_with_drift(v1, base_dir, runtime=runtime)


def enrich_with_drift(
    response: SpineQueryResponse,
    base_dir: str,
    *,
    runtime: Optional["BrainMemoryRuntime"] = None,
) -> SpineQueryResponse:
    trace_id = response.trace_id
    runtime_events = get_execution_tap().events_for_trace_merged(trace_id)
    spine_events = query_by_trace(base_dir, trace_id, limit=5000)

    detector = RuntimeSpineDriftDetector()
    drift = detector.compare(trace_id, runtime_events, spine_events)

    annotator = DriftAnnotator()
    annotated_events = annotator.annotate_events(
        response.events,
        drift,
        runtime_events=runtime_events if runtime_events else None,
    )

    response.events = annotated_events
    response.schema_version = SCHEMA_VERSION_V2

    exec_graph = build_execution_graph(trace_id, annotated_events)
    response.explanation = bind_explanation_to_execution_v2(
        response.explanation,
        exec_graph,
        annotated_events,
        fusion_v2=response.fusion_v2,
        drift_summary=drift.summary(),
    )

    healer = SpineHealer()
    heal = healer.heal_from_drift(drift, runtime_events)

    response.meta = {
        **response.meta,
        "drift_engine": "runtime-spine-v1",
        "drift_summary": drift.summary(),
        "drift_report": drift.to_dict(),
        "heal_suggestions": heal["suggestions"],
        "heal_result": heal["backfill"],
        "self_heal_enabled": heal["self_heal_enabled"],
    }
    return apply_explain_v3(response)


def get_drift_report(base_dir: str, trace_id: str) -> dict[str, Any]:
    runtime_events = get_execution_tap().events_for_trace_merged(trace_id)
    spine_events = query_by_trace(base_dir, trace_id, limit=5000)
    detector = RuntimeSpineDriftDetector()
    return detector.compare(trace_id, runtime_events, spine_events).to_dict()


def apply_explain_v3(response: SpineQueryResponse) -> SpineQueryResponse:
    from core.spine.explain_v3 import build_drift_aware_explanation

    drift_summary = response.meta.get("drift_summary")
    execution_v2 = response.explanation.get("execution_v2")
    explain_v3 = build_drift_aware_explanation(
        response.trace_id,
        response.events,
        fusion_v2=response.fusion_v2,
        drift_summary=drift_summary if isinstance(drift_summary, dict) else None,
        execution_v2=execution_v2 if isinstance(execution_v2, dict) else None,
    )
    response.explanation = {
        **response.explanation,
        "explain_v3": explain_v3,
        "v3_summary": explain_v3["summary"],
        "narrative": explain_v3["summary"],
        "causal_story": explain_v3.get("causal_story") or response.explanation.get("causal_story"),
        "state_story": explain_v3.get("state_story") or response.explanation.get("state_story"),
        "control_story": explain_v3.get("control_story") or response.explanation.get("control_story"),
    }
    response.meta = {**response.meta, "explain_engine": "explain-v3"}
    try:
        narrative = str(explain_v3.get("summary") or explain_v3.get("narrative") or "")
        from core.spine.token.hooks import emit_tokens_for_explain

        emit_tokens_for_explain(response.trace_id, narrative)
    except Exception:
        pass
    return response
