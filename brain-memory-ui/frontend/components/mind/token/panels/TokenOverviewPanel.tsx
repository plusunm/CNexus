"use client";

import { bi, biFmt, biSection, tokenL } from "@/lib/spine/labels";
import { COST_COLOR, groupByMode } from "@/lib/token/format";
import type { TokenTrace } from "@/lib/token/types";
import { useMindTheme } from "../../MindUiProvider";

type Props = {
  traces: TokenTrace[];
};

export function TokenOverviewPanel({ traces }: Props) {
  const t = useMindTheme();
  const totalTokens = traces.reduce((s, d) => s + d.total, 0);
  const totalIn = traces.reduce((s, d) => s + d.tokens_in, 0);
  const totalOut = traces.reduce((s, d) => s + d.tokens_out, 0);
  const spikes = traces.filter((d) => d.cost_level === "spike");
  const highs = traces.filter((d) => d.cost_level === "high");
  const modes = groupByMode(traces.map((x) => ({ mode: x.mode, total: x.total })));

  const stats = [
    { label: bi(tokenL.totalTokens), value: totalTokens },
    { label: bi(tokenL.tokensIn), value: totalIn },
    { label: bi(tokenL.tokensOut), value: totalOut },
    { label: bi(tokenL.activeTraces), value: traces.length },
    { label: bi(tokenL.spikeCount), value: spikes.length },
    { label: bi(tokenL.highCostCount), value: highs.length },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
        {stats.map((s) => (
          <div
            key={s.label}
            className="rounded-lg border p-3"
            style={{ borderColor: t.border, backgroundColor: t.chatBg }}
          >
            <p className="text-[10px] uppercase tracking-wider opacity-60" style={{ color: t.textMuted }}>
              {s.label}
            </p>
            <p className="text-lg font-semibold font-mono mt-1" style={{ color: t.text }}>
              {s.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Section title={biSection(tokenL.spikes)} border={t.border} surface={t.surface} text={t.text} muted={t.textMuted}>
          {spikes.length === 0 ? (
            <p className="text-xs opacity-60" style={{ color: t.textMuted }}>
              {bi(tokenL.noAnomalies)}
            </p>
          ) : (
            <div className="space-y-2">
              {spikes.map((trace) => (
                <TraceRow key={trace.trace_id} trace={trace} />
              ))}
            </div>
          )}
        </Section>

        <Section title={biSection(tokenL.distribution)} border={t.border} surface={t.surface} text={t.text} muted={t.textMuted}>
          <div className="space-y-1">
            {traces.slice(0, 15).map((trace) => (
              <TraceRow key={trace.trace_id} trace={trace} compact />
            ))}
          </div>
        </Section>
      </div>

      <Section title={biSection(tokenL.modeCostMap)} border={t.border} surface={t.surface} text={t.text} muted={t.textMuted}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {modes.map((m) => (
            <div
              key={m.mode}
              className="flex justify-between text-sm border-b py-1.5 font-mono"
              style={{ borderColor: t.border, color: t.text }}
            >
              <span>{m.mode}</span>
              <span style={{ color: t.blue }}>{m.totalTokens}</span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Section({
  title,
  children,
  border,
  surface,
}: {
  title: string;
  children: React.ReactNode;
  border: string;
  surface: string;
  text: string;
  muted: string;
}) {
  return (
    <div className="rounded-xl border p-4" style={{ borderColor: border, backgroundColor: surface }}>
      <h3 className="text-[10px] uppercase tracking-wider mb-3 opacity-60">{title}</h3>
      {children}
    </div>
  );
}

function TraceRow({ trace, compact }: { trace: TokenTrace; compact?: boolean }) {
  const color = COST_COLOR[trace.cost_level] ?? "#94a3b8";
  return (
    <div className="flex justify-between items-start border-b py-1.5 text-xs font-mono" style={{ borderColor: "rgba(128,128,128,0.2)" }}>
      <div>
        <span style={{ color: "#e2e8f0" }}>{trace.trace_id.slice(0, compact ? 10 : 20)}</span>
        {!compact ? (
          <p className="text-[10px] opacity-50 mt-0.5">
            {biFmt(tokenL.traceIoLine, {
              in: trace.tokens_in,
              out: trace.tokens_out,
              mode: trace.mode,
            })}
          </p>
        ) : null}
      </div>
      <span style={{ color }}>{trace.total}</span>
    </div>
  );
}
