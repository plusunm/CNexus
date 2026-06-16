"""Explain v3 — drift-corrected epistemic narrative."""

from __future__ import annotations

from typing import Any

EXPLAIN_V3_VERSION = "explain-v3"


def _events_by_id(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(e.get("event_id") or ""): e for e in events if e.get("event_id")}


def _annotate_story_line(line: str, events: dict[str, dict[str, Any]]) -> str:
    for eid, ev in events.items():
        if eid and eid in line:
            status = ev.get("drift_status")
            if status and status != "OK":
                conf = ev.get("confidence")
                suffix = f" [{status}"
                if conf is not None:
                    suffix += f" · conf={conf:.2f}"
                suffix += "]"
                return line + suffix
    return line


def build_drift_aware_explanation(
    trace_id: str,
    events: list[dict[str, Any]],
    *,
    fusion_v2: dict[str, Any] | None = None,
    drift_summary: dict[str, Any] | None = None,
    execution_v2: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = dict((fusion_v2 or {}).get("explanation") or {})
    by_id = _events_by_id(events)

    caveats: list[str] = []
    for ev in events:
        status = ev.get("drift_status")
        etype = ev.get("event_type") or ev.get("type") or "event"
        eid = ev.get("event_id") or "?"
        if status == "MISSING":
            caveats.append(f"Runtime recorded {etype} ({eid}) but spine log may be incomplete.")
        elif status == "EXTRA":
            caveats.append(f"Spine lists {etype} ({eid}) without matching runtime tap evidence.")
        elif status == "SUSPECT":
            caveats.append(f"{etype} ({eid}) semantics differ between runtime and spine.")

    score = float((drift_summary or {}).get("score") or 1.0)
    missing_n = int((drift_summary or {}).get("missing_count") or 0)
    extra_n = int((drift_summary or {}).get("extra_count") or 0)
    mismatch_n = int((drift_summary or {}).get("mismatch_count") or 0)

    causal_story = [
        _annotate_story_line(str(s), by_id) for s in (base.get("causal_story") or [])
    ]
    state_story = [
        _annotate_story_line(str(s), by_id) for s in (base.get("state_story") or [])
    ]
    control_story = [
        _annotate_story_line(str(s), by_id) for s in (base.get("control_story") or [])
    ]

    summary = str(base.get("summary") or f"Trace {trace_id}: execution narrative.")
    if score < 0.95 and (missing_n or extra_n or mismatch_n):
        summary += (
            f" Epistemic confidence {score:.0%}"
            f" ({missing_n} missing, {extra_n} extra, {mismatch_n} suspect in spine vs runtime)."
        )
    elif score < 1.0:
        summary += f" Verified alignment {score:.0%} against runtime tap."

    path_note = ""
    if execution_v2 and execution_v2.get("path_frames"):
        phases = [f"{f.get('phase')}:{f.get('event_type')}" for f in execution_v2["path_frames"]]
        path_note = " Execution path: " + " → ".join(phases) + "."
        if any(f.get("drift_status") not in (None, "OK") for f in execution_v2["path_frames"]):
            path_note += " Some steps flagged by drift overlay."

    return {
        "version": EXPLAIN_V3_VERSION,
        "trace_id": trace_id,
        "summary": summary + path_note,
        "causal_story": causal_story,
        "state_story": state_story,
        "control_story": control_story,
        "caveats": caveats,
        "epistemic_score": round(score, 4),
        "drift_summary": drift_summary,
    }
