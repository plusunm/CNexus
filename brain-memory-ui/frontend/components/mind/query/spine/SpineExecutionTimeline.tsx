"use client";

import type { DriftStatus, SpineFrontContractV1, SpineEventView } from "@/lib/spine/contract";
import { bi, biSection, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../../MindUiProvider";

const TYPE_COLORS: Record<string, string> = {
  dispatch: "#60a5fa",
  control: "#fbbf24",
  recall: "#34d399",
  llm_call: "#a78bfa",
  memory_mutation: "#f472b6",
  state: "#2dd4bf",
  chat: "#38bdf8",
  write_intent: "#94a3b8",
};

function formatTime(ts?: number) {
  if (!ts) return "—";
  return new Date(ts).toLocaleTimeString();
}

function causalHint(event: SpineEventView): string | null {
  const edges = event.causal_edges?.filter((e) => e.relation === "triggered_by") ?? [];
  if (!edges.length) return null;
  return `↳ ${edges[0].relation} · ${bi(spineL.triggeredBy)} ${edges[0].from.slice(0, 10)}`;
}

function driftStyles(status: DriftStatus | undefined, t: ReturnType<typeof useMindTheme>) {
  switch (status) {
    case "MISSING":
      return { borderColor: t.red, backgroundColor: `${t.red}18` };
    case "EXTRA":
      return { borderColor: t.orange, backgroundColor: t.chatBg };
    case "SUSPECT":
      return { borderColor: "#fb923c", backgroundColor: t.chatBg, borderStyle: "dashed" as const };
    default:
      return null;
  }
}

function driftLabel(status: DriftStatus | undefined): string | null {
  if (!status || status === "OK") return null;
  if (status === "MISSING") return bi(spineL.driftStatusMissing);
  if (status === "EXTRA") return bi(spineL.driftStatusExtra);
  if (status === "SUSPECT") return bi(spineL.driftStatusSuspect);
  return status;
}

type Props = {
  contract: SpineFrontContractV1;
  onSelectEvent?: (id: string) => void;
  selectedEventId?: string | null;
};

export function SpineExecutionTimeline({ contract, onSelectEvent, selectedEventId }: Props) {
  const t = useMindTheme();
  const events = contract.execution.timeline.length
    ? contract.execution.timeline
    : contract.events;

  return (
    <section className="p-4 border-b" style={{ borderColor: t.border }}>
      <h3 className="text-[10px] uppercase tracking-wider mb-3 opacity-60" style={{ color: t.textMuted }}>
        {biSection(spineL.timeline)}
      </h3>
      {events.length === 0 ? (
        <p className="text-sm opacity-60" style={{ color: t.textMuted }}>
          {bi(spineL.noExecutionEvents)}
        </p>
      ) : (
        <div className="space-y-2 max-h-[42vh] overflow-auto pr-1">
          {events.map((ev) => {
            const color = TYPE_COLORS[ev.type] ?? t.textMuted;
            const hint = causalHint(ev);
            const hasDelta = Boolean(ev.state_delta?.change_count ?? ev.state_delta?.changes);
            const selected = selectedEventId === ev.event_id;
            const driftStyle = driftStyles(ev.drift_status, t);
            const dLabel = driftLabel(ev.drift_status);
            return (
              <button
                key={ev.event_id}
                type="button"
                onClick={() => onSelectEvent?.(ev.event_id)}
                className="w-full text-left rounded-lg border px-3 py-2.5 transition"
                style={{
                  borderColor: selected ? "#5eead4" : driftStyle?.borderColor ?? t.border,
                  backgroundColor: selected ? t.sidebarActive : driftStyle?.backgroundColor ?? t.chatBg,
                  borderStyle: driftStyle?.borderStyle,
                }}
              >
                <div className="flex items-center justify-between gap-2 text-[10px] font-mono">
                  <span style={{ color: t.textMuted }}>{formatTime(ev.timestamp)}</span>
                  <div className="flex items-center gap-2">
                    {dLabel ? (
                      <span className="text-[9px] opacity-80" style={{ color: driftStyle?.borderColor }}>
                        {dLabel}
                      </span>
                    ) : null}
                    {ev.confidence != null && ev.drift_status && ev.drift_status !== "OK" ? (
                      <span className="opacity-50">
                        {bi(spineL.driftConfidence)}: {ev.confidence.toFixed(2)}
                      </span>
                    ) : null}
                    <span className="font-semibold" style={{ color }}>
                      {ev.type}
                    </span>
                  </div>
                </div>
                <p className="text-xs mt-1 leading-snug" style={{ color: t.text }}>
                  {ev.summary ?? ev.event_id}
                </p>
                {hint ? (
                  <p className="text-[10px] mt-1 font-mono opacity-70" style={{ color: "#5eead4" }}>
                    {hint}
                  </p>
                ) : null}
                {hasDelta ? (
                  <span
                    className="inline-block mt-1.5 text-[9px] px-1.5 py-0.5 rounded font-mono"
                    style={{ backgroundColor: `${t.green}22`, color: t.green }}
                  >
                    {bi(spineL.stateDelta)}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
