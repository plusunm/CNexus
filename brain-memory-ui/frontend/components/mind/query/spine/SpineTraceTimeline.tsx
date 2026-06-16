"use client";

import type { SpineFrontContractV1 } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  contract: SpineFrontContractV1;
  selectedEventId?: string | null;
  onSelectEvent?: (id: string) => void;
};

function formatTime(ts?: number) {
  if (!ts) return "—";
  return new Date(ts).toLocaleTimeString();
}

export function SpineTraceTimeline({ contract, selectedEventId, onSelectEvent }: Props) {
  const t = useMindTheme();
  const frames = contract.explanation.execution_v2?.path_frames;
  const events =
    frames?.length
      ? frames.map((f) => {
          const ev = contract.events.find((e) => e.event_id === f.event_id);
          return {
            event_id: f.event_id,
            type: f.event_type,
            phase: f.phase,
            summary: f.summary ?? ev?.summary,
            drift_status: f.drift_status,
            timestamp: ev?.timestamp,
          };
        })
      : (contract.execution.timeline.length ? contract.execution.timeline : contract.events).map((e) => ({
          event_id: e.event_id,
          type: e.type,
          phase: contract.execution.dag.nodes.find((n) => n.event_id === e.event_id)?.phase ?? "",
          summary: e.summary,
          drift_status: e.drift_status,
          timestamp: e.timestamp,
        }));

  return (
    <div className="h-full flex flex-col min-h-0">
      <h3 className="text-[10px] uppercase tracking-wider mb-2 opacity-60 shrink-0" style={{ color: t.textMuted }}>
        {biSection(spineL.traceTimeline)}
      </h3>
      <p className="text-[10px] font-mono mb-2 opacity-50 shrink-0" style={{ color: t.textMuted }}>
        {contract.trace_id} ─
      </p>
      {events.length === 0 ? (
        <p className="text-xs opacity-60" style={{ color: t.textMuted }}>
          {bi(spineL.noExecutionEvents)}
        </p>
      ) : (
        <div className="flex-1 overflow-auto space-y-0.5 pr-1 font-mono text-[11px]">
          {events.map((ev, i) => {
            const isLast = i === events.length - 1;
            const prefix = isLast ? "└─" : "├─";
            const selected = selectedEventId === ev.event_id;
            return (
              <button
                key={ev.event_id}
                type="button"
                onClick={() => onSelectEvent?.(ev.event_id)}
                className="w-full text-left pl-3 py-1.5 rounded transition"
                style={{
                  backgroundColor: selected ? t.sidebarActive : "transparent",
                  color: t.text,
                }}
              >
                <span className="opacity-50 mr-1">{prefix}</span>
                <span className="font-semibold" style={{ color: "#60a5fa" }}>
                  {ev.type}
                </span>
                {ev.phase ? (
                  <span className="opacity-50 ml-1">· {ev.phase}</span>
                ) : null}
                {ev.drift_status && ev.drift_status !== "OK" ? (
                  <span className="ml-1 text-[9px]" style={{ color: t.red }}>
                    [{ev.drift_status}]
                  </span>
                ) : null}
                <div className="pl-4 opacity-70 truncate">{ev.summary ?? ev.event_id.slice(0, 12)}</div>
                <div className="pl-4 opacity-40 text-[9px]">{formatTime(ev.timestamp)}</div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
