"""Identity-aware Spine Query Engine v3."""

from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING

from core.spine.identity.service import get_identity_service
from core.spine.query.builder_v2 import enrich_with_drift, run_query_v2
from core.spine.query.types import SpineQueryResponse

SCHEMA_VERSION_V3 = "spine-query-3"

if TYPE_CHECKING:
    from brain_memory.runtime import BrainMemoryRuntime


def run_query_v3(
    base_dir: str,
    *,
    query: str | None = None,
    trace_id: str | None = None,
    mode: str = "causal",
    limit: int = 200,
    runtime: Optional["BrainMemoryRuntime"] = None,
    token_influence: bool = False,
) -> SpineQueryResponse:
    v2 = run_query_v2(
        base_dir,
        query=query,
        trace_id=trace_id,
        mode=mode,
        limit=limit,
        runtime=runtime,
    )
    v3 = enrich_with_identity(v2, base_dir)
    if token_influence:
        return enrich_with_token_influence(v3, base_dir)
    return v3


def enrich_with_token_influence(
    response: SpineQueryResponse,
    base_dir: str,
) -> SpineQueryResponse:
    from core.spine.token.service import build_trace_token_report

    report = build_trace_token_report(base_dir, response.trace_id)
    causal = report.get("causal") or {}
    influence = report.get("influence") or {}
    response.meta = {
        **response.meta,
        "token_influence": True,
        "token_field": {
            "total_cost": report.get("total_cost"),
            "by_phase": report.get("by_phase"),
        },
        "influence": influence,
    }
    if causal.get("edges"):
        response.causal = {**response.causal, "token_weighted_edges": causal["edges"]}
    return response


def enrich_with_identity(
    response: SpineQueryResponse,
    base_dir: str,
) -> SpineQueryResponse:
    svc = get_identity_service()
    identity = svc.resolve_for_response(
        response.trace_id,
        response.events,
        control=response.control,
        state=response.state,
        execution=response.execution,
        base_dir=base_dir,
    )

    response.schema_version = SCHEMA_VERSION_V3
    response.meta = {
        **response.meta,
        "identity_engine": identity["version"],
        "identity": identity,
    }

    drift_summary = response.meta.get("drift_summary")
    if isinstance(drift_summary, dict):
        drift_summary = dict(drift_summary)
        drift_summary["identity"] = identity["identity"]
        drift_summary["identity_drift"] = identity.get("identity_drift", False)
        drift_summary["identity_mismatch"] = identity.get("identity_mismatch", False)
        response.meta["drift_summary"] = drift_summary

    explain_v3 = dict(response.explanation.get("explain_v3") or {})
    note_parts = [
        f"Execution identity {identity['identity']} (provable sameness class, distinct from trace_id)."
    ]
    if identity.get("equivalent_traces"):
        note_parts.append(
            "Equivalent traces: " + ", ".join(identity["equivalent_traces"]) + "."
        )
    if identity.get("drift_variants"):
        note_parts.append(
            "Drift variants (same trigger, different identity): "
            + ", ".join(identity["drift_variants"])
            + "."
        )
    if identity.get("identity_drift"):
        note_parts.append("Identity drift detected — replay may not match this identity hash.")

    explain_v3["identity_note"] = " ".join(note_parts)
    explain_v3["identity"] = identity
    summary = str(response.explanation.get("v3_summary") or response.explanation.get("narrative") or "")
    if explain_v3["identity_note"] not in summary:
        explain_v3["summary"] = summary + " " + explain_v3["identity_note"]
    else:
        explain_v3["summary"] = summary

    response.explanation = {
        **response.explanation,
        "explain_v3": explain_v3,
        "v3_summary": explain_v3["summary"],
        "narrative": explain_v3["summary"],
    }
    return response


def get_identity_report(base_dir: str, trace_id: str) -> dict[str, Any]:
    from core.spine.query.builder import run_query

    v1 = run_query(base_dir, trace_id=trace_id)
    v3 = enrich_with_identity(
        enrich_with_drift(v1, base_dir),
        base_dir,
    )
    return v3.meta.get("identity") or {}
