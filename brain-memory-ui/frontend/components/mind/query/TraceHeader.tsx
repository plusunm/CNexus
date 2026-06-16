"use client";

import type { TraceContext } from "@/lib/spine/contract";
import { bi, spineL } from "@/lib/spine/labels";
import { useMindTheme } from "../MindUiProvider";

type Props = {
  trace: TraceContext | null;
  latencyMs?: number;
  liveConnected?: boolean;
};

const STATUS_COLOR: Record<string, string> = {
  LIVE: "#34d399",
  REPLAY: "#60a5fa",
  OFFLINE: "#94a3b8",
  STALE: "#fbbf24",
};

function statusLabel(status: TraceContext["status"], liveConnected?: boolean): string {
  if (liveConnected || status === "LIVE") return bi(spineL.statusLive);
  if (status === "REPLAY") return bi(spineL.statusReplay);
  if (status === "STALE") return bi(spineL.statusStale);
  return bi(spineL.statusOffline);
}

export function TraceHeader({ trace, latencyMs, liveConnected }: Props) {
  const t = useMindTheme();

  if (!trace) {
    return (
      <div
        className="rounded-lg border px-3 py-2 text-[11px] font-mono opacity-60"
        style={{ borderColor: t.border, color: t.textMuted }}
      >
        {bi(spineL.trace)}: — · {bi(spineL.status)}: {bi(spineL.statusOffline)} · {bi(spineL.source)}:{" "}
        {spineL.executionSource.en}
      </div>
    );
  }

  const status = liveConnected ? "LIVE" : trace.status;
  const statusColor = STATUS_COLOR[status] ?? t.textMuted;

  return (
    <div
      className="rounded-lg border px-3 py-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono"
      style={{ borderColor: t.border, backgroundColor: t.chatBg }}
    >
      <span style={{ color: t.text }}>
        {bi(spineL.trace)}: <span className="opacity-90">{trace.trace_id}</span>
      </span>
      <span>
        {bi(spineL.status)}:{" "}
        <span style={{ color: statusColor }}>{statusLabel(status, liveConnected)}</span>
      </span>
      <span style={{ color: t.textMuted }}>
        {bi(spineL.source)}: {trace.source}
      </span>
      <span style={{ color: t.textMuted }}>
        {bi(spineL.mode)}: {spineL.executionMode.en}
      </span>
      <span style={{ color: t.textMuted }}>
        {bi(spineL.events)}: {trace.event_count}
      </span>
      {trace.semantic_edge_count != null ? (
        <span style={{ color: t.textMuted }}>
          {bi(spineL.semantic)}: {trace.semantic_edge_count}
        </span>
      ) : null}
      {latencyMs != null ? (
        <span style={{ color: t.textMuted }}>{latencyMs}ms</span>
      ) : null}
    </div>
  );
}
