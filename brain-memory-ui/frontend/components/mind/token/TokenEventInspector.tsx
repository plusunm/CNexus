"use client";

import { bi, biFmt, tokenL } from "@/lib/spine/labels";
import { COST_COLOR, PHASE_COLOR, SOURCE_COLOR } from "@/lib/token/format";
import type { TokenEventRow, TokenField } from "@/lib/token/types";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  report: TokenField | null;
  selectedEventId: string | null;
};

export function TokenEventInspector({ report, selectedEventId }: Props) {
  const t = useMindTheme();
  const events = report?.token_events ?? [];
  const ev: TokenEventRow | undefined = selectedEventId
    ? events.find((e) => e.event_id === selectedEventId || e.spine_event_id === selectedEventId)
    : undefined;

  if (!report) {
    return (
      <p className="text-xs opacity-60" style={{ color: t.textMuted }}>
        {bi(tokenL.selectTrace)}
      </p>
    );
  }

  if (!ev) {
    return (
      <div className="space-y-3 text-xs" style={{ color: t.textMuted }}>
        <p className="text-[10px] uppercase tracking-wider opacity-60">{bi(tokenL.inspector)}</p>
        <p>{bi(tokenL.selectEventHint)}</p>
        <div className="font-mono space-y-1 pt-2 border-t" style={{ borderColor: t.border, color: t.text }}>
          <p>{bi(tokenL.traceSummary)}: {report.trace_id}</p>
          <p>{bi(tokenL.totalCost)}: {report.total_cost}</p>
          <p>{bi(tokenL.eventsCount)}: {events.length}</p>
          <p>{bi(tokenL.bindings)}: {report.bindings?.length ?? 0}</p>
        </div>
      </div>
    );
  }

  const sourceColor = SOURCE_COLOR[ev.source] ?? t.blue;
  const phaseColor = PHASE_COLOR[ev.phase] ?? t.textMuted;

  const rows: { k: string; v: string }[] = [
    { k: "event_id", v: ev.event_id },
    { k: "source", v: ev.source },
    { k: "phase", v: ev.phase },
    { k: "tokens_in", v: String(ev.tokens_in) },
    { k: "tokens_out", v: String(ev.tokens_out) },
    { k: "total", v: String(ev.total) },
    { k: "spine_event_id", v: ev.spine_event_id ?? "—" },
    { k: "causal_edge_id", v: ev.causal_edge_id ?? "—" },
    { k: "identity_id", v: ev.identity_id ?? report.identity_id ?? "—" },
    { k: "mode", v: ev.mode ?? "—" },
    { k: "entry", v: ev.entry ?? "—" },
    { k: "cost_level", v: ev.cost_level ?? "—" },
  ];

  return (
    <div className="space-y-3">
      <p className="text-[10px] uppercase tracking-wider opacity-60" style={{ color: t.textMuted }}>
        {bi(tokenL.inspector)}
      </p>

      <div className="flex flex-wrap gap-1.5">
        <Badge label={ev.source} color={sourceColor} />
        <Badge label={ev.phase} color={phaseColor} />
        {ev.cost_level ? (
          <Badge label={ev.cost_level} color={COST_COLOR[ev.cost_level]} />
        ) : null}
      </div>

      <div className="space-y-2">
        <Block title={bi(tokenL.whatHappened)} text={t.text} muted={t.textMuted} border={t.border}>
          {biFmt(tokenL.consumedSummary, {
            source: ev.source,
            total: ev.total,
            in: ev.tokens_in,
            out: ev.tokens_out,
          })}
        </Block>
        <Block title={bi(tokenL.whoTriggered)} text={t.text} muted={t.textMuted} border={t.border}>
          {ev.entry || ev.mode || bi(tokenL.runtimeFallback)}
        </Block>
        <Block title={bi(tokenL.whatChanged)} text={t.text} muted={t.textMuted} border={t.border}>
          {biFmt(tokenL.boundToSpine, { id: ev.spine_event_id ?? "—" })}
          {ev.causal_edge_id ? ` · ${biFmt(tokenL.boundEdge, { id: ev.causal_edge_id })}` : ""}
        </Block>
      </div>

      <div className="rounded border overflow-hidden text-[10px] font-mono" style={{ borderColor: t.border }}>
        {rows.map((r) => (
          <div
            key={r.k}
            className="flex justify-between px-2 py-1 border-b"
            style={{ borderColor: t.border, color: t.text }}
          >
            <span className="opacity-50">{r.k}</span>
            <span className="truncate max-w-[58%] text-right">{r.v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded font-semibold"
      style={{ backgroundColor: `${color}22`, color }}
    >
      {label}
    </span>
  );
}

function Block({
  title,
  children,
  text,
  muted,
  border,
}: {
  title: string;
  children: React.ReactNode;
  text: string;
  muted: string;
  border: string;
}) {
  return (
    <div className="rounded border p-2" style={{ borderColor: border }}>
      <p className="text-[9px] uppercase tracking-wider mb-1" style={{ color: muted }}>
        {title}
      </p>
      <p className="text-xs" style={{ color: text }}>
        {children}
      </p>
    </div>
  );
}
