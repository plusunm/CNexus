"use client";

import clsx from "clsx";
import { ChevronRight } from "lucide-react";
import { eventTypeLabel } from "@/lib/spineMapper";
import type { SpineEvent } from "@/lib/spineTypes";
import { useSpineStore } from "@/lib/spineStore";
import { bi, debuggerL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

function DecisionBadge({ decision }: { decision?: SpineEvent["decision"] }) {
  const t = useMindTheme();
  if (!decision) return null;
  const color =
    decision.decision === "ALLOW" ? t.green : decision.decision === "WARN" ? t.orange : t.red;
  return (
    <span
      className="text-[9px] px-1.5 py-0.5 rounded font-medium"
      style={{ backgroundColor: `${color}22`, color }}
    >
      {decision.decision}
    </span>
  );
}

function SpineEventRow({ event, depth = 0 }: { event: SpineEvent; depth?: number }) {
  const t = useMindTheme();
  const selectedEventId = useSpineStore((s) => s.selectedEventId);
  const selectEvent = useSpineStore((s) => s.selectEvent);
  const active = selectedEventId === event.event_id;
  const time = new Date(event.timestamp).toLocaleTimeString("zh-CN", { hour12: false });

  return (
    <button
      type="button"
      onClick={() => selectEvent(event.event_id)}
      className={clsx("w-full text-left rounded-lg border transition mb-1", active && "ring-1")}
      style={{
        marginLeft: depth * 12,
        borderColor: active ? t.blue : t.border,
        backgroundColor: active ? t.sidebarActive : t.surface,
        boxShadow: active ? `0 0 0 1px ${t.blue}` : undefined,
      }}
    >
      <div className="flex items-center gap-2 px-3 py-2">
        <span className="text-[10px] font-mono shrink-0 w-[62px]" style={{ color: t.textLight }}>
          {time}
        </span>
        <span
          className="text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0"
          style={{ backgroundColor: t.purpleSoft, color: t.purple }}
        >
          {eventTypeLabel(event.event_type)}
        </span>
        <span className="text-[11px] flex-1 truncate" style={{ color: t.text }}>
          {event.summary}
        </span>
        <DecisionBadge decision={event.decision} />
        <ChevronRight className="w-3.5 h-3.5 shrink-0 opacity-40" />
      </div>
      <div className="px-3 pb-2 flex flex-wrap gap-2 text-[9px]" style={{ color: t.textMuted }}>
        <span>{event.action}</span>
        <span>·</span>
        <span>{event.subsystem}</span>
        {event.write_intent && (
          <>
            <span>·</span>
            <span>{event.write_intent.mutability}</span>
            {event.write_intent.shadow && <span className="text-orange-400">shadow</span>}
          </>
        )}
        <span className="font-mono ml-auto">{event.trace_id.slice(0, 10)}…</span>
      </div>
    </button>
  );
}

type Props = { events: SpineEvent[] };

/** Elastic APM 式 waterfall 时间轴 — Spine 主投影 */
export function SpineTimelinePanel({ events }: Props) {
  const t = useMindTheme();
  const replayIndex = useSpineStore((s) => s.replayIndex);
  const streamMode = useSpineStore((s) => s.streamMode);

  const slice =
    streamMode === "replay" ? events.slice(0, Math.max(1, replayIndex + 1)) : events;

  const byTrace = new Map<string, SpineEvent[]>();
  for (const e of slice) {
    const list = byTrace.get(e.trace_id) ?? [];
    list.push(e);
    byTrace.set(e.trace_id, list);
  }

  if (events.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <p className="text-sm" style={{ color: t.textMuted }}>
          {bi(debuggerL.noSpineEvents)}
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 min-h-0">
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-medium" style={{ color: t.text }}>
          Event Spine
        </p>
        <p className="text-[10px] font-mono" style={{ color: t.textMuted }}>
          {slice.length} events · {byTrace.size} traces
        </p>
      </div>

      {[...byTrace.entries()].map(([traceId, traceEvents]) => (
        <div key={traceId} className="mb-4">
          <div
            className="text-[10px] font-mono mb-2 px-2 py-1 rounded inline-block"
            style={{ backgroundColor: t.blueSoft, color: t.blue }}
          >
            TRACE {traceId}
          </div>
          {traceEvents.map((e) => (
            <SpineEventRow key={e.event_id} event={e} />
          ))}
        </div>
      ))}
    </div>
  );
}
