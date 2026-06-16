"use client";

import type { ControlDecisionView, SpineEventView } from "@/lib/spine/contract";
import { useQueryStore } from "@/lib/queryStore";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  events: SpineEventView[];
  decisions: ControlDecisionView[];
};

export function InspectorView({ events, decisions }: Props) {
  const t = useMindTheme();
  const { selectedEventId, setSelectedEventId } = useQueryStore();

  const selected =
    events.find((e) => e.event_id === selectedEventId) ??
    (selectedEventId ? events[0] : null);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-4 min-h-[50vh]">
      <div className="space-y-1 max-h-[60vh] overflow-auto">
        <p className="text-[10px] uppercase tracking-wider opacity-60 mb-2">Events</p>
        {events.map((ev) => (
          <button
            key={ev.event_id}
            type="button"
            onClick={() => setSelectedEventId(ev.event_id)}
            className="w-full text-left text-[11px] font-mono px-2 py-1.5 rounded border truncate"
            style={{
              borderColor: selectedEventId === ev.event_id ? "#5eead4" : t.border,
              backgroundColor: selectedEventId === ev.event_id ? t.sidebarActive : "transparent",
              color: t.textMuted,
            }}
          >
            {ev.type} · {ev.event_id.slice(0, 16)}
          </button>
        ))}
      </div>

      <div className="min-w-0">
        {!selected ? (
          <p className="text-sm opacity-70">Select an execution event to inspect spine truth.</p>
        ) : (
          <div className="space-y-3">
            <h4 className="text-xs font-semibold" style={{ color: t.text }}>
              {selected.type} · {selected.event_id}
            </h4>
            <pre
              className="text-[11px] overflow-auto max-h-[55vh] p-3 rounded-lg border"
              style={{ borderColor: t.border, backgroundColor: t.chatBg }}
            >
              {JSON.stringify(
                {
                  event_type: selected.type,
                  trace_id: selected.trace_id,
                  summary: selected.summary,
                  entry: selected.entry,
                  decision: selected.decision,
                  payload: selected.payload,
                  state_delta: selected.state_delta,
                  causal_edges: selected.causal_edges,
                  raw: selected.raw,
                },
                null,
                2,
              )}
            </pre>
          </div>
        )}

        {decisions.length ? (
          <div className="mt-4 pt-4 border-t" style={{ borderColor: t.border }}>
            <p className="text-[10px] uppercase tracking-wider opacity-60 mb-2">Control decisions</p>
            <ul className="text-xs font-mono space-y-1">
              {decisions.map((d) => (
                <li key={d.event_id}>
                  {d.decision} · {d.entry ?? d.rule ?? d.event_id}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}
