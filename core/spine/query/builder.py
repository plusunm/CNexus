"""Spine Query facade — single entry for API and tests."""

from __future__ import annotations

from core.spine.execution.bind_v2 import bind_explanation_to_execution_v2, build_execution_graph
from core.spine.explain_v2 import build_fusion_explanation
from core.spine.query.causal_index import CausalIndex
from core.spine.query.causal_v2 import SemanticCausalIndex
from core.spine.query.engine import extract_control, extract_state, query_by_trace
from core.spine.query.explain import explain_trace
from core.spine.query.parser import resolve_query
from core.spine.query.subgraph import build_subgraph, find_root_cause_summary
from core.spine.query.types import ParsedQuery, SpineQueryResponse
from core.spine.query.validate import validate_trace
from core.spine.state.timeline import StateTimelineEngine


def run_query(
    base_dir: str,
    *,
    query: str | None = None,
    trace_id: str | None = None,
    mode: str = "causal",
    limit: int = 200,
) -> SpineQueryResponse:
    parsed = resolve_query(query=query, trace_id=trace_id, mode=mode, limit=limit)
    return run_parsed_query(base_dir, parsed)


def run_parsed_query(base_dir: str, parsed: ParsedQuery) -> SpineQueryResponse:
    events = query_by_trace(base_dir, parsed.trace_id, limit=parsed.limit)
    subgraph = build_subgraph(events)
    edges = subgraph["edges"]

    index = CausalIndex()
    index.build(events)
    semantic = SemanticCausalIndex()
    semantic.build(events)
    timeline_engine = StateTimelineEngine()
    state_timeline = timeline_engine.build(events)
    root_summary = find_root_cause_summary(events, index)

    control = extract_control(events)
    state = extract_state(events)
    explanation = explain_trace(
        parsed.trace_id,
        events,
        mode=parsed.mode,
        edges=edges,
        root_summary=root_summary,
    )

    fusion_v2 = build_fusion_explanation(parsed.trace_id, events, causal_index=index)
    explanation = {
        **explanation,
        "v2_summary": fusion_v2["explanation"].get("summary"),
        "causal_story": fusion_v2["explanation"].get("causal_story"),
        "state_story": fusion_v2["explanation"].get("state_story"),
        "control_story": fusion_v2["explanation"].get("control_story"),
    }

    exec_graph = build_execution_graph(parsed.trace_id, events)
    explanation = bind_explanation_to_execution_v2(
        explanation,
        exec_graph,
        events,
        fusion_v2=fusion_v2,
    )

    return SpineQueryResponse(
        trace_id=parsed.trace_id,
        mode=parsed.mode,
        events=events,
        edges=edges,
        control=control,
        state=state,
        explanation=explanation,
        fusion_v2=fusion_v2,
        subgraph=subgraph,
        causal={
            "index_version": "v2",
            "roots": root_summary.get("roots", []),
            "chains": root_summary.get("chains", []),
            "structural": {
                "enabled": True,
                "roots": root_summary.get("roots", []),
                "chains": root_summary.get("chains", []),
            },
            "semantic": semantic.to_dict(),
        },
        execution=exec_graph.to_dict(),
        meta={
            "source": "spine_events.jsonl",
            "event_count": len(events),
            "edge_count": len(edges),
            "semantic_edge_count": len(semantic.edges),
            "node_count": len(subgraph.get("nodes") or []),
            "fusion_version": fusion_v2.get("version"),
            "state_timeline": state_timeline,
            "trace_validation": validate_trace(parsed.trace_id, events),
        },
    )
