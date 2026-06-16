"""CP-2 Explanation Engine v1 — deterministic rule templates (no LLM)."""

from __future__ import annotations

from typing import Any

from core.spine.query.types import ExplainMode


def explain_trace(
    trace_id: str,
    events: list[dict[str, Any]],
    *,
    mode: ExplainMode = "causal",
    edges: list[dict[str, Any]] | None = None,
    root_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not events:
        return {
            "narrative": f"No spine events found for trace {trace_id}.",
            "rules": ["empty_trace"],
            "mode": mode,
        }

    kinds = [str(e.get("event_type") or "event") for e in events]
    chain = " → ".join(kinds[:8])
    if len(kinds) > 8:
        chain += f" → … (+{len(kinds) - 8})"

    rules: list[str] = []
    if any(str(e.get("event_type")) == "control" or e.get("decision") for e in events):
        rules.append("control_path_detected")
    if any(e.get("state_delta") for e in events):
        rules.append("state_mutation_detected")
    if any(str(e.get("decision")) == "WARN" for e in events):
        rules.append("warn_decision_detected")
    if any(str(e.get("decision")) == "REJECT" for e in events):
        rules.append("reject_decision_detected")
    if edges:
        rules.append(f"causal_edges:{len(edges)}")

    roots = (root_summary or {}).get("roots") or []
    chains = (root_summary or {}).get("chains") or []
    if roots:
        rules.append(f"root_events:{len(roots)}")
    if chains:
        rules.append(f"root_chains:{len(chains)}")

    root_note = ""
    if roots:
        root_note = f" Structural roots: {', '.join(roots[:3])}."
    elif chains:
        root_note = f" Deepest ancestor for leaf events tracked ({len(chains)} chains)."

    if mode == "control":
        control_count = sum(
            1 for e in events if str(e.get("event_type")) == "control" or e.get("decision")
        )
        narrative = (
            f"Trace {trace_id}: {control_count} control decision(s) "
            f"across {len(events)} events."
        )
    elif mode == "state":
        delta_count = sum(1 for e in events if e.get("state_delta"))
        narrative = (
            f"Trace {trace_id}: {delta_count} state delta record(s) "
            f"across {len(events)} events."
        )
    elif mode == "explain":
        narrative = (
            f"Trace {trace_id}: execution summary — {chain}. "
            f"Rules applied for causal explanation."
        )
    elif mode == "linear":
        narrative = (
            f"Trace {trace_id}: linear sequence of {len(events)} events. "
            f"Order: {chain}."
        )
    elif mode == "event":
        narrative = (
            f"Trace {trace_id}: {len(events)} events indexed. "
            f"Types present: {', '.join(sorted(set(kinds)))}."
        )
    else:
        narrative = (
            f"Trace {trace_id}: {len(events)} events in causal chain. "
            f"Execution flow: {chain}.{root_note}"
        )

    return {
        "narrative": narrative,
        "rules": rules,
        "mode": mode,
        "root_causes": {
            "roots": roots,
            "chains": chains,
        },
    }
