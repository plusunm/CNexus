"use client";

import clsx from "clsx";
import type { SpineEventView } from "@/lib/spine/contract";
import { useQueryStore } from "@/lib/queryStore";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  events: SpineEventView[];
};

function formatTime(ts?: number) {
  if (!ts) return "—";
  return new Date(ts).toLocaleTimeString();
}

export function ExecutionTimelineView({ events }: Props) {
  const t = useMindTheme();
  const { selectedEventId, setSelectedEventId } = useQueryStore();

  if (!events.length) {
    return <p className="text-sm opacity-70">No execution spine events for this trace.</p>;
  }

  return (
    <div className="space-y-1 max-h-[65vh] overflow-auto">
      {events.map((ev) => {
        const selected = selectedEventId === ev.event_id;
        return (
          <button
            key={ev.event_id}
            type="button"
            onClick={() => setSelectedEventId(ev.event_id)}
            className={clsx(
              "w-full text-left rounded-lg border px-3 py-2 transition",
              selected ? "ring-1" : "hover:opacity-100 opacity-90",
            )}
            style={{
              borderColor: selected ? "#5eead4" : t.border,
              backgroundColor: selected ? t.sidebarActive : t.chatBg,
            }}
          >
            <div className="flex items-baseline gap-2 text-[10px] font-mono opacity-60">
              <span>{formatTime(ev.timestamp)}</span>
              <span style={{ color: "#5eead4" }}>[{ev.type}]</span>
            </div>
            <p className="text-xs mt-0.5 truncate" style={{ color: t.text }}>
              {ev.summary ?? ev.event_id}
            </p>
          </button>
        );
      })}
    </div>
  );
}
