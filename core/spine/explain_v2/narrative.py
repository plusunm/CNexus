"""Rule-based narrative synthesis from fused causal/state/control structures."""

from __future__ import annotations

from typing import Any


class NarrativeSynthesizerV2:
    def synthesize(
        self,
        *,
        trace_id: str,
        causal_chain: list[dict[str, Any]],
        state_transitions: list[dict[str, Any]],
        control_flow: list[dict[str, Any]],
    ) -> dict[str, Any]:
        causal_story: list[str] = []
        for node in causal_chain:
            etype = node.get("type") or "event"
            caused = node.get("caused") or []
            if caused:
                causal_story.append(
                    f"{etype} ({node['event_id']}) caused {', '.join(caused)}"
                )
            else:
                causal_story.append(f"{etype} ({node['event_id']}) recorded")

        state_story: list[str] = []
        for st in state_transitions:
            eid = st.get("event_id")
            delta = st.get("delta") or {}
            if not delta:
                continue
            parts: list[str] = []
            for key, val in delta.items():
                if isinstance(val, (int, float)):
                    parts.append(f"{key} {val:+.4g}" if val != 0 else f"{key} unchanged")
                else:
                    parts.append(f"{key} updated")
            state_story.append(f"{eid}: " + ", ".join(parts))

        control_story: list[str] = []
        for cf in control_flow:
            policy = cf.get("policy") or "policy"
            decision = cf.get("decision") or "UNKNOWN"
            control_story.append(f"{policy} → {decision} at {cf.get('event_id')}")

        summary_parts: list[str] = []
        if causal_story:
            summary_parts.append("causal propagation")
        if state_story:
            summary_parts.append("state transformation")
        if control_story:
            summary_parts.append("control evaluation")

        if summary_parts:
            summary = (
                f"Trace {trace_id}: "
                + "; ".join(summary_parts)
                + "."
            )
        else:
            summary = f"Trace {trace_id}: insufficient fused evidence for semantic explanation."

        if causal_chain and state_transitions and control_flow:
            summary += (
                " User-path events linked state change under supervisory control."
            )
        elif causal_chain and state_transitions:
            summary += " State changed along the structural causal chain."
        elif causal_chain and control_flow:
            summary += " Control decisions applied along the event chain."

        return {
            "summary": summary,
            "causal_story": causal_story,
            "state_story": state_story,
            "control_story": control_story,
        }
